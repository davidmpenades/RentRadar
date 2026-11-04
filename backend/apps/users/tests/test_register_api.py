import json
import logging
import re
from contextlib import ExitStack, contextmanager
from unittest import mock

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.handlers.wsgi import LimitedStream
from django.db import connection

from apps.users import views
from apps.users.models import User
from apps.users.throttling import RegistrationThrottle
from apps.users.views import public_field_errors

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/register/"
JSON = "application/json"
EMAIL = "ana@correo.es"
PASSWORD = "vela roja en el puerto"
CREDENTIALS = {"email": EMAIL, "password": PASSWORD}
TOKEN = "a1B2c3D4" * 4
OTHER_TOKEN = "z9Y8x7W6" * 4
SESSION_COOKIE = django_settings.SESSION_COOKIE_NAME
CSRF_COOKIE = django_settings.CSRF_COOKIE_NAME
FOURTEEN_DAYS = 60 * 60 * 24 * 14
MAX_BYTES = 4096
LIMIT = 10
HOUR = 3600
SURROGATE = chr(0xD800)
# Un objeto anidado unos 600 niveles en una clave desconocida, dentro de 4096 bytes
NESTED = '{"x":' * 600 + "{}" + "}" * 600


def register(client, body=None, *, token=TOKEN, cookie=TOKEN, method="post", **extra):
    if body is None:
        body = CREDENTIALS
    if not isinstance(body, str):
        body = json.dumps(body)
    if cookie is not None:
        client.cookies[CSRF_COOKIE] = cookie
    headers = {} if token is None else {"X-CSRFToken": token}
    # El cliente de Django mandaría el cuerpo de GET y HEAD como cadena de consulta
    if method in ("get", "head"):
        return getattr(client, method)(URL, headers=headers, **extra)
    return getattr(client, method)(
        URL, data=body, content_type=JSON, headers=headers, **extra
    )


def no_session(client):
    return None


def anonymous_session(client):
    store = SessionStore()
    store["basket"] = "kept-before"
    store.create()
    client.cookies[SESSION_COOKIE] = store.session_key
    return store.session_key


def logged_in_session(client):
    member = User.objects.create(email="luis@correo.es")
    client.force_login(member)
    session = client.session
    session["basket"] = "kept-before"
    session.save()
    return client.cookies[SESSION_COOKIE].value


SESSIONS = pytest.mark.parametrize(
    "prepare",
    [no_session, anonymous_session, logged_in_session],
    ids=["without-session", "anonymous-session", "logged-in-session"],
)


def stored_sessions():
    return list(
        Session.objects.order_by("session_key").values_list(
            "session_key", "session_data", "expire_date"
        )
    )


@contextmanager
def untouchable_session_store():
    # Cualquier lectura o escritura de la sesión hace fallar la petición
    names = ("load", "save", "create", "delete", "flush", "cycle_key", "clear")
    with ExitStack() as stack:
        for name in names:
            stack.enter_context(
                mock.patch.object(
                    SessionStore, name, side_effect=AssertionError(f"session.{name}")
                )
            )
        yield


def session_of(response):
    key = response.cookies[SESSION_COOKIE].value
    return key, Session.objects.get(session_key=key).get_decoded()


def assert_no_store(response):
    assert response["Cache-Control"] == "no-store"


def cross_origin_headers(response):
    return [n for n in response.headers if n.lower().startswith("access-control-")]


# --- Alta correcta ------------------------------------------------------------


def test_a_valid_registration_answers_201_with_only_the_normalized_email(
    csrf_client,
):
    response = register(
        csrf_client, {"email": "  Ana@Correo.ES ", "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json() == {"user": {"email": EMAIL}}
    user = User.objects.get()
    assert user.email == EMAIL
    assert user.check_password(PASSWORD)
    assert_no_store(response)


def test_the_session_cookie_is_http_only_lax_for_fourteen_days_on_the_root_path(
    csrf_client,
):
    response = register(csrf_client)

    cookie = response.cookies[SESSION_COOKIE]
    assert cookie.value
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["max-age"] == FOURTEEN_DAYS
    assert cookie["path"] == "/"


def test_a_new_csrf_token_comes_in_a_cookie_the_page_can_read(csrf_client):
    response = register(csrf_client)

    cookie = response.cookies[CSRF_COOKIE]
    assert cookie.value != TOKEN
    assert re.fullmatch(r"[A-Za-z0-9]{32}", cookie.value)
    assert not cookie["httponly"]


def test_the_new_session_belongs_to_the_created_account(csrf_client):
    response = register(csrf_client)

    _, decoded = session_of(response)
    assert decoded[SESSION_KEY] == str(User.objects.get(email=EMAIL).pk)
    assert Session.objects.count() == 1


def test_the_session_cookie_varies_the_answer(csrf_client):
    response = register(csrf_client)

    assert "Cookie" in response["Vary"]


def test_privileged_fields_ids_and_unknown_fields_are_ignored(csrf_client):
    body = {
        **CREDENTIALS,
        "id": 999_999,
        "pk": 999_999,
        "is_staff": True,
        "is_superuser": True,
        "is_active": False,
        "groups": [1],
        "user_permissions": [1],
        "last_login": "2020-01-01T00:00:00Z",
        "date_joined": "2020-01-01T00:00:00Z",
        "user": {"id": 1, "email": "otro@correo.es"},
        "role": "admin",
    }

    response = register(csrf_client, body)

    assert response.status_code == 201
    assert response.json() == {"user": {"email": EMAIL}}
    user = User.objects.get()
    assert user.pk != 999_999
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_active is True
    assert not user.groups.exists()
    assert not user.user_permissions.exists()


def test_credentials_at_the_root_next_to_a_nested_unknown_key_are_registered(
    csrf_client,
):
    body = json.dumps(CREDENTIALS)[:-1] + ', "x": ' + NESTED + "}"
    assert len(body.encode()) <= MAX_BYTES

    response = register(csrf_client, body)

    assert response.status_code == 201
    assert response.json() == {"user": {"email": EMAIL}}


def test_a_failure_opening_the_session_leaves_no_account(csrf_client, monkeypatch):
    # La cuenta y la fila de la sesión nueva se crean en la misma transacción
    class SessionCreateFailed(Exception):
        pass

    def failing_create(self):
        raise SessionCreateFailed

    monkeypatch.setattr(SessionStore, "create", failing_create)

    with pytest.raises(SessionCreateFailed):
        register(csrf_client)

    assert User.objects.count() == 0


# --- La sesión anterior se descarta siempre -----------------------------------


def assert_replaced_by_a_session_of_the_new_account(response, old_key):
    assert response.status_code == 201
    new_key, decoded = session_of(response)
    assert new_key != old_key
    assert not Session.objects.filter(session_key=old_key).exists()
    assert response.cookies[CSRF_COOKIE].value != TOKEN
    assert decoded[SESSION_KEY] == str(User.objects.get(email=EMAIL).pk)
    assert "basket" not in decoded


def test_an_anonymous_session_with_data_is_discarded(csrf_client):
    old_key = anonymous_session(csrf_client)

    response = register(csrf_client)

    assert_replaced_by_a_session_of_the_new_account(response, old_key)


def test_a_session_of_another_account_is_discarded(csrf_client):
    old_key = logged_in_session(csrf_client)

    response = register(csrf_client)

    assert_replaced_by_a_session_of_the_new_account(response, old_key)


def test_a_session_of_the_same_account_is_discarded_too(csrf_client, monkeypatch):
    # login() conserva la clave si la sesión ya es de esa cuenta: solo flush() la cambia
    user = User.objects.create(email=EMAIL)
    csrf_client.force_login(user)
    session = csrf_client.session
    session["basket"] = "kept-before"
    session.save()
    old_key = csrf_client.cookies[SESSION_COOKIE].value
    monkeypatch.setattr(views, "register_user", lambda *, email, password: user)

    response = register(csrf_client)

    assert_replaced_by_a_session_of_the_new_account(response, old_key)


# --- Rechazo por validación ---------------------------------------------------


def test_a_rejection_lists_every_field_code_without_the_values(csrf_client):
    response = register(
        csrf_client, {"email": "ana.correo.es", "password": "1234567890"}
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "invalid_fields",
        "params": {
            "email": ["email_invalid"],
            "password": ["password_too_common", "password_entirely_numeric"],
        },
    }
    assert "ana.correo.es" not in response.content.decode()
    assert "1234567890" not in response.content.decode()
    assert User.objects.count() == 0
    assert_no_store(response)


def test_an_existing_email_is_rejected_explicitly_with_the_other_codes(csrf_client):
    User.objects.create(email=EMAIL)

    response = register(csrf_client, {"email": "Ana@Correo.ES", "password": "corta"})

    assert response.json() == {
        "code": "invalid_fields",
        "params": {"email": ["email_taken"], "password": ["password_too_short"]},
    }
    assert User.objects.count() == 1


@SESSIONS
def test_a_rejected_registration_leaves_the_session_untouched(csrf_client, prepare):
    key = prepare(csrf_client)
    accounts = User.objects.count()
    before = stored_sessions()

    with untouchable_session_store():
        response = register(csrf_client, {"email": "ana", "password": "corta"})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "invalid_fields"
    assert list(body["params"]) == ["email", "password"]
    assert SESSION_COOKIE not in response.cookies
    assert stored_sessions() == before
    assert User.objects.count() == accounts
    if key is not None:
        assert csrf_client.cookies[SESSION_COOKIE].value == key


def test_an_email_of_four_kilobytes_is_too_long_without_a_server_error(csrf_client):
    body = {"email": "a" * 4000 + "@correo.es", "password": PASSWORD}
    assert len(json.dumps(body).encode()) <= MAX_BYTES

    response = register(csrf_client, body)

    # El validador de Django rechaza también un email de más de 320 caracteres
    assert response.status_code == 400
    assert response.json() == {
        "code": "invalid_fields",
        "params": {"email": ["email_invalid", "email_too_long"]},
    }
    assert User.objects.count() == 0


def test_an_object_nested_in_an_unknown_key_goes_on_to_validation(csrf_client):
    assert len(NESTED.encode()) <= MAX_BYTES

    response = register(csrf_client, NESTED)

    assert response.status_code == 400
    assert response.json() == {
        "code": "invalid_fields",
        "params": {"email": ["email_empty"], "password": ["password_required"]},
    }


HOSTILE = {
    "nul-in-the-email": (
        {"email": "ana\x00@correo.es", "password": PASSWORD},
        {"email": ["email_invalid", "email_control_char"]},
    ),
    "surrogate-in-the-email": (
        {"email": f"ana@{SURROGATE}.es", "password": PASSWORD},
        {"email": ["email_invalid"]},
    ),
    "nul-in-the-password": (
        {"email": EMAIL, "password": f"vela\x00roja{PASSWORD}"},
        {"password": ["password_invalid"]},
    ),
    "surrogate-in-the-password": (
        {"email": EMAIL, "password": SURROGATE},
        {"password": ["password_invalid"]},
    ),
    "missing-fields": (
        {},
        {"email": ["email_empty"], "password": ["password_required"]},
    ),
    "null-fields": (
        {"email": None, "password": None},
        {"email": ["email_empty"], "password": ["password_required"]},
    ),
    "empty-fields": (
        {"email": "", "password": ""},
        {"email": ["email_empty"], "password": ["password_required"]},
    ),
}


@pytest.mark.parametrize(("body", "params"), HOSTILE.values(), ids=HOSTILE.keys())
def test_hostile_or_empty_fields_are_field_errors_and_never_a_server_error(
    csrf_client, body, params
):
    # json.dumps escapa el nulo y el sustituto: el cuerpo viaja en ASCII
    response = register(csrf_client, json.dumps(body))

    assert response.status_code == 400
    assert response.json() == {"code": "invalid_fields", "params": params}
    assert User.objects.count() == 0


def test_an_empty_json_body_is_an_empty_object(csrf_client):
    # Con el cuerpo vacío el cliente de Django no pone el tipo: se pasa a mano
    response = register(csrf_client, "", CONTENT_TYPE=JSON)

    assert response.json() == {
        "code": "invalid_fields",
        "params": {"email": ["email_empty"], "password": ["password_required"]},
    }


MALFORMED = {
    "invalid-json": ("{not json", {}, 400, "invalid_request"),
    "root-list": ("[]", {}, 400, "invalid_request"),
    "deep-lists": ("[" * 2048 + "]" * 2048, {}, 400, "invalid_request"),
    "email-number": ('{"email": 5, "password": "x"}', {}, 400, "invalid_request"),
    "password-list": ('{"email": "a", "password": ["x"]}', {}, 400, "invalid_request"),
    "password-object": ('{"email": "a", "password": {}}', {}, 400, "invalid_request"),
    "too-large-declared": ("{" + " " * 5000 + "}", {}, 413, "payload_too_large"),
    "chunked": (
        "{}",
        {"HTTP_TRANSFER_ENCODING": "chunked"},
        413,
        "payload_too_large",
    ),
}


@pytest.mark.parametrize(
    ("body", "extra", "status", "code"), MALFORMED.values(), ids=MALFORMED.keys()
)
def test_a_malformed_or_too_large_body_is_rejected_with_its_general_code(
    csrf_client, body, extra, status, code
):
    response = register(csrf_client, body, **extra)

    assert response.status_code == status
    assert response.json() == {"code": code}
    assert_no_store(response)
    assert User.objects.count() == 0


def test_a_body_that_is_not_json_is_an_invalid_request(csrf_client):
    csrf_client.cookies[CSRF_COOKIE] = TOKEN

    response = csrf_client.post(
        URL,
        data=json.dumps(CREDENTIALS),
        content_type="text/plain",
        headers={"X-CSRFToken": TOKEN},
    )

    assert response.json() == {"code": "invalid_request"}
    assert User.objects.count() == 0


def test_public_field_errors_orders_the_fields_and_renames_the_general_ones():
    errors = public_field_errors(
        {
            "__all__": ["constraint_violated", "validation_failed"],
            "password": ["password_too_short", "password_too_common"],
            "email": ["email_invalid", "email_control_char"],
        }
    )

    assert list(errors) == ["email", "password", "non_field"]
    assert errors == {
        "email": ["email_invalid", "email_control_char"],
        "password": ["password_too_short", "password_too_common"],
        "non_field": ["constraint_violated", "validation_failed"],
    }


def test_public_field_errors_leaves_out_the_fields_without_errors():
    assert public_field_errors({"password": ["password_required"]}) == {
        "password": ["password_required"]
    }


# --- Métodos ------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete", "options", "head"])
def test_every_other_method_gets_405_with_allow_post(csrf_client, method):
    response = register(csrf_client, method=method, token=None)

    assert response.status_code == 405
    assert response["Allow"] == "POST"
    assert_no_store(response)
    if method != "head":
        assert response.json() == {"code": "method_not_allowed"}
    assert User.objects.count() == 0


# --- CSRF ---------------------------------------------------------------------

CSRF_REJECTED = {
    "no-header": {"token": None},
    "empty-header": {"token": ""},
    "no-cookie": {"cookie": None},
    "header-differs-from-cookie": {"token": OTHER_TOKEN},
}


@SESSIONS
@pytest.mark.parametrize("variant", CSRF_REJECTED.values(), ids=CSRF_REJECTED.keys())
def test_without_a_valid_token_nothing_is_created_and_the_session_is_untouched(
    csrf_client, prepare, variant
):
    key = prepare(csrf_client)
    accounts = User.objects.count()
    before = stored_sessions()

    with untouchable_session_store():
        response = register(csrf_client, **variant)

    assert response.status_code == 403
    assert response.json() == {"code": "csrf_failed"}
    assert_no_store(response)
    assert SESSION_COOKIE not in response.cookies
    assert stored_sessions() == before
    assert User.objects.count() == accounts
    if key is not None:
        assert csrf_client.cookies[SESSION_COOKIE].value == key


def test_a_foreign_origin_is_rejected_even_with_a_valid_token(csrf_client):
    response = register(csrf_client, HTTP_ORIGIN="http://evil.test")

    assert response.json() == {"code": "csrf_failed"}
    assert User.objects.count() == 0


def test_the_body_is_not_read_before_the_csrf_check(csrf_client):
    with mock.patch.object(LimitedStream, "read", side_effect=AssertionError):
        response = register(csrf_client, token=None)

    assert response.json() == {"code": "csrf_failed"}


# --- Límite sobre el endpoint real --------------------------------------------


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake = Clock()
    # staticmethod: sin él Python pasaría la instancia como primer argumento
    monkeypatch.setattr(RegistrationThrottle, "timer", staticmethod(fake))
    return fake


def assert_throttled(response):
    assert response.status_code == 429
    body = response.json()
    assert set(body) == {"code", "retry_after"}
    assert body["code"] == "throttled"
    assert isinstance(body["retry_after"], int)
    assert body["retry_after"] >= 1
    assert response["Retry-After"] == str(body["retry_after"])
    assert_no_store(response)


PRIOR_REQUESTS = {
    "no-csrf-header": (lambda c: register(c, token=None), 403, "csrf_failed"),
    "token-differs-from-cookie": (
        lambda c: register(c, token=OTHER_TOKEN),
        403,
        "csrf_failed",
    ),
    "declared-too-large": (
        lambda c: register(c, "{" + " " * 5000 + "}"),
        413,
        "payload_too_large",
    ),
    "chunked": (
        lambda c: register(c, "{}", HTTP_TRANSFER_ENCODING="chunked"),
        413,
        "payload_too_large",
    ),
    "invalid-json": (lambda c: register(c, "{not json"), 400, "invalid_request"),
    "short-password": (
        lambda c: register(c, {"email": EMAIL, "password": "corta"}),
        400,
        "invalid_fields",
    ),
    "put": (lambda c: register(c, method="put"), 405, "method_not_allowed"),
}


@pytest.mark.parametrize(
    ("send", "status", "code"), PRIOR_REQUESTS.values(), ids=PRIOR_REQUESTS.keys()
)
def test_ten_rejected_requests_use_up_the_quota_of_the_real_endpoint(
    csrf_client, clock, send, status, code
):
    for _ in range(LIMIT):
        response = send(csrf_client)
        assert response.status_code == status
        assert response.json()["code"] == code

    assert_throttled(register(csrf_client))
    assert User.objects.count() == 0


def test_ten_registrations_use_up_the_quota_and_the_eleventh_creates_nothing(
    csrf_client, clock
):
    for index in range(LIMIT):
        body = {"email": f"ana{index}@correo.es", "password": PASSWORD}
        assert register(csrf_client, body).status_code == 201

    assert_throttled(register(csrf_client))
    assert not User.objects.filter(email=EMAIL).exists()


# --- Caché y respuestas mínimas -----------------------------------------------


def throttled_answer(client):
    for _ in range(LIMIT):
        register(client, token=None)
    return register(client)


EVERY_ANSWER = {
    "201": (register, 201),
    "400-invalid-fields": (lambda c: register(c, {"email": "", "password": ""}), 400),
    "400-invalid-request": (lambda c: register(c, "[]"), 400),
    "403": (lambda c: register(c, token=None), 403),
    "405": (lambda c: register(c, method="put"), 405),
    "413": (lambda c: register(c, "{" + " " * 5000 + "}"), 413),
    "429": (throttled_answer, 429),
}


@pytest.mark.parametrize(("send", "status"), EVERY_ANSWER.values(), ids=EVERY_ANSWER)
def test_no_answer_can_be_stored_by_a_cache(csrf_client, clock, send, status):
    response = send(csrf_client)

    assert response.status_code == status
    assert_no_store(response)


@pytest.mark.parametrize(("send", "status"), EVERY_ANSWER.values(), ids=EVERY_ANSWER)
def test_no_answer_grants_cross_origin_access(csrf_client, clock, send, status):
    response = send(csrf_client)

    assert response.status_code == status
    assert not cross_origin_headers(response)


def test_a_preflight_from_another_origin_gets_405_without_cross_origin_headers(
    csrf_client,
):
    response = csrf_client.options(
        URL,
        headers={
            "Origin": "http://evil.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, x-csrftoken",
        },
    )

    assert response.status_code == 405
    assert not cross_origin_headers(response)


def test_the_success_carries_only_the_new_email_even_after_a_staff_session(
    csrf_client,
):
    staff = User.objects.create(
        email="staff@correo.es", is_staff=True, is_superuser=True
    )
    csrf_client.force_login(staff)

    response = register(csrf_client)

    body = response.json()
    assert list(body) == ["user"]
    assert list(body["user"]) == ["email"]
    assert body["user"]["email"] == EMAIL
    text = response.content.decode()
    for hidden in ("id", "staff", "superuser", "last_login", "date_joined", "active"):
        assert hidden not in text


@pytest.mark.parametrize(
    ("send", "keys"),
    [
        (lambda c: register(c, {"email": "", "password": ""}), {"code", "params"}),
        (lambda c: register(c, "[]"), {"code"}),
        (lambda c: register(c, token=None), {"code"}),
        (lambda c: register(c, method="put"), {"code"}),
    ],
    ids=["invalid-fields", "invalid-request", "csrf-failed", "method-not-allowed"],
)
def test_errors_carry_only_their_planned_keys(csrf_client, send, keys):
    csrf_client.force_login(
        User.objects.create(email="staff@correo.es", is_staff=True, is_superuser=True)
    )

    response = send(csrf_client)

    assert set(response.json()) == keys
    assert "staff@correo.es" not in response.content.decode()


# --- Logs ---------------------------------------------------------------------

# La marca no aparece en ningún identificador: el traceback imprime el código fuente
MARK = "zq7x"
MARKED_EMAIL = f"{MARK}.ana@correo.es"
MARKED_PASSWORD = f"{MARK} vela roja en el puerto"


def test_neither_the_email_nor_the_password_reach_the_logs_or_the_counter(
    csrf_client, caplog, monkeypatch
):
    # Condición previa: con el SQL en DEBUG el INSERT llevaría el email y el hash
    backends = logging.getLogger("django.db.backends")
    assert backends.getEffectiveLevel() >= logging.INFO
    assert connection.force_debug_cursor is False
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(connection, "force_debug_cursor", True)
    marked = {"email": MARKED_EMAIL, "password": MARKED_PASSWORD}

    created = register(csrf_client, marked)
    rejections = [
        register(csrf_client, marked),
        register(csrf_client, {"email": MARKED_EMAIL, "password": MARK}),
        register(csrf_client, {"email": f"{MARK}\x00", "password": MARKED_PASSWORD}),
        register(csrf_client, marked, token=None),
        register(csrf_client, json.dumps(marked) + " " * MAX_BYTES),
        register(csrf_client, json.dumps(marked)[:-1]),
    ]

    assert created.status_code == 201
    assert [response.status_code for response in rejections] == [
        400,
        400,
        400,
        403,
        413,
        400,
    ]
    assert [r for r in caplog.records if r.name == "django.request"]
    assert MARK not in caplog.text.lower()
    for response in rejections:
        assert MARK not in response.content.decode().lower()
    keys = [str(key) for key in cache._cache]
    assert [key for key in keys if "throttle_register_" in key]
    assert not [key for key in keys if MARK in key.lower()]
