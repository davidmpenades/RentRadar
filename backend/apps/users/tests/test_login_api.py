import json
import logging
import re
from datetime import timedelta
from unittest import mock

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.hashers import make_password
from django.contrib.auth.signals import user_logged_out, user_login_failed
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.cache import caches
from django.core.handlers.wsgi import LimitedStream
from django.db import connection
from django.test import Client
from django.utils import timezone
from django.views.debug import ExceptionReporter

from apps.users import views
from apps.users.models import User
from apps.users.tests.helpers import (
    Clock,
    assert_no_store,
    assert_throttled,
    cross_origin_headers,
    stored_sessions,
    untouchable_session_store,
)
from apps.users.throttling import (
    LOGIN_CACHE_ALIAS,
    LoginFailureLimit,
    LoginIpThrottle,
    login_pair_key,
)

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/login/"
SESSION_URL = "/api/v1/auth/session/"
JSON = "application/json"
EMAIL = "ana@correo.es"
OTHER_EMAIL = "luis@correo.es"
PASSWORD = "vela roja en el puerto"
WRONG_PASSWORD = "vela azul en el puerto"
CREDENTIALS = {"email": EMAIL, "password": PASSWORD}
TOKEN = "a1B2c3D4" * 4
OTHER_TOKEN = "z9Y8x7W6" * 4
SESSION_COOKIE = django_settings.SESSION_COOKIE_NAME
CSRF_COOKIE = django_settings.CSRF_COOKIE_NAME
FOURTEEN_DAYS = 60 * 60 * 24 * 14
MAX_BYTES = 4096
SURROGATE = chr(0xD800)
# Barra invertida con chr: el escape octal de la cookie no debe interpretarse aquí
OCTAL_NULL = chr(92) + "000"
# Formato válido de clave de sesión, sin fila en la BD
KEY_WITHOUT_ROW = "k3y5in4f1l4" * 3
CREDENTIALS_REJECTED = {
    "code": "invalid_fields",
    "params": {"non_field": ["credentials_invalid"]},
}
WRONG_PASSWORD_BODY = {"email": EMAIL, "password": WRONG_PASSWORD}
NULL_CHARACTER = chr(0)
IP_LIMIT = 20
PAIR_LIMIT = 5
MINUTE = 60
PAIR_WAIT = 15 * 60
# El cliente de pruebas de Django envía desde 127.0.0.1
LOCAL_BUCKET = "127.0.0.1"
FOREIGN_ORIGIN = "http://evil.test"
HIDDEN = "********************"
# La marca no aparece en ningún identificador: el traceback imprime el código fuente
MARK = "zq7x"


def send(client, body=None, *, token=TOKEN, cookie=TOKEN, method="post", **extra):
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


def account(email=EMAIL, password=PASSWORD, **fields):
    return User.objects.create(email=email, password=make_password(password), **fields)


def no_session(client):
    return None


def anonymous_session(client):
    store = SessionStore()
    store["basket"] = "kept-before"
    store.create()
    client.cookies[SESSION_COOKIE] = store.session_key
    return store.session_key


def session_of(client, user):
    client.force_login(user)
    session = client.session
    session["basket"] = "kept-before"
    session.save()
    return client.cookies[SESSION_COOKIE].value


def another_account_session(client):
    return session_of(client, User.objects.create(email=OTHER_EMAIL))


def same_account_session(client):
    return session_of(client, User.objects.get(email=EMAIL))


def staff_session(client):
    staff = User.objects.create(
        email="staff@correo.es", is_staff=True, is_superuser=True
    )
    return session_of(client, staff)


def short_session_cookie(client):
    client.cookies[SESSION_COOKIE] = "abc"
    return "abc"


def unknown_session_key(client):
    client.cookies[SESSION_COOKIE] = KEY_WITHOUT_ROW
    return KEY_WITHOUT_ROW


def forbid_credential_checks(monkeypatch):
    check = mock.Mock(side_effect=AssertionError("check_credentials"))
    monkeypatch.setattr(views, "check_credentials", check)
    return check


@pytest.fixture
def credentials_never_checked(monkeypatch):
    return forbid_credential_checks(monkeypatch)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    # Un solo reloj para los dos límites: las esperas no dependen de la hora real
    fake = Clock()
    # staticmethod: sin él Python pasaría la instancia como primer argumento
    monkeypatch.setattr(LoginIpThrottle, "timer", staticmethod(fake))
    monkeypatch.setattr(LoginFailureLimit, "timer", staticmethod(fake))
    return fake


def fail(client, body=WRONG_PASSWORD_BODY, *, times=PAIR_LIMIT, **extra):
    for _ in range(times):
        assert send(client, body, **extra).status_code == 400


def reject_by_csrf(client, *, times=IP_LIMIT):
    for _ in range(times):
        assert send(client, token=None).status_code == 403


def ip_limited_answer(client):
    reject_by_csrf(client)
    return send(client)


def pair_limited_answer(client):
    fail(client)
    return send(client)


# --- Entrada correcta ---------------------------------------------------------


def test_a_valid_login_answers_200_with_only_the_stored_email(csrf_client):
    account()

    response = send(csrf_client, {"email": "  Ana@Correo.ES ", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json() == {"user": {"email": EMAIL}}
    assert_no_store(response)


def test_the_session_cookie_is_http_only_lax_for_fourteen_days_on_the_root_path(
    csrf_client,
):
    account()

    cookie = send(csrf_client).cookies[SESSION_COOKIE]

    assert cookie.value
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["max-age"] == FOURTEEN_DAYS
    assert cookie["path"] == "/"


def test_a_new_csrf_token_comes_in_a_cookie_the_page_can_read(csrf_client):
    account()

    cookie = send(csrf_client).cookies[CSRF_COOKIE]

    assert cookie.value != TOKEN
    assert re.fullmatch(r"[A-Za-z0-9]{32}", cookie.value)
    assert not cookie["httponly"]


def test_the_new_session_belongs_to_the_account(csrf_client):
    user = account()

    key = send(csrf_client).cookies[SESSION_COOKIE].value

    decoded = Session.objects.get(session_key=key).get_decoded()
    assert decoded[SESSION_KEY] == str(user.pk)
    assert Session.objects.count() == 1


def test_the_session_cookie_varies_the_answer(csrf_client):
    account()

    assert "Cookie" in send(csrf_client)["Vary"]


def test_who_am_i_returns_the_email_after_logging_in(csrf_client):
    account()

    send(csrf_client)

    assert csrf_client.get(SESSION_URL).json() == {"user": {"email": EMAIL}}


def test_logging_in_writes_last_login(csrf_client):
    user = account()
    assert user.last_login is None

    send(csrf_client)

    user.refresh_from_db()
    assert user.last_login is not None


def test_the_success_carries_only_the_email_even_for_a_staff_account(csrf_client):
    account(is_staff=True, is_superuser=True)

    response = send(csrf_client)

    body = response.json()
    assert list(body) == ["user"]
    assert list(body["user"]) == ["email"]
    text = response.content.decode()
    for hidden in ("id", "staff", "superuser", "last_login", "date_joined", "active"):
        assert hidden not in text


# --- Credenciales erróneas: una sola respuesta --------------------------------

# (campos de la cuenta que existe, cuerpo enviado)
WRONG_CREDENTIALS = {
    "unknown-email": ({}, {"email": OTHER_EMAIL, "password": PASSWORD}),
    "email-absent": ({}, {"password": PASSWORD}),
    "email-null": ({}, {"email": None, "password": PASSWORD}),
    "email-empty": ({}, {"email": "", "password": PASSWORD}),
    "email-blank": ({}, {"email": "   ", "password": PASSWORD}),
    "email-null-character": ({}, {"email": "ana\x00@correo.es", "password": PASSWORD}),
    "email-lone-surrogate": (
        {},
        {"email": f"ana{SURROGATE}@correo.es", "password": PASSWORD},
    ),
    "email-without-at-sign": ({}, {"email": "ana", "password": PASSWORD}),
    "email-4000-characters": (
        {},
        {"email": "a" * 4000 + "@correo.es", "password": PASSWORD},
    ),
    "wrong-password": ({}, {"email": EMAIL, "password": WRONG_PASSWORD}),
    "empty-password": ({}, {"email": EMAIL, "password": ""}),
    "password-129-code-points": ({}, {"email": EMAIL, "password": "a" * 129}),
    "password-lone-surrogate": ({}, {"email": EMAIL, "password": f"vela{SURROGATE}"}),
    "inactive-account": ({"is_active": False}, CREDENTIALS),
    "unusable-password": ({"password": None}, CREDENTIALS),
}

COOKIE_STATES = {
    "without-session": no_session,
    "valid-session": anonymous_session,
    "short-session-cookie": short_session_cookie,
    "unknown-session-key": unknown_session_key,
}


def comparable(response):
    headers = {name: value for name, value in response.headers.items()}
    headers.pop("Date", None)
    # Las cookies se comparan por nombre y atributos: su valor cambia en cada petición
    cookies = {name: dict(morsel.items()) for name, morsel in response.cookies.items()}
    return response.status_code, response.content, headers, cookies


@pytest.mark.parametrize("cause", WRONG_CREDENTIALS, ids=WRONG_CREDENTIALS)
@pytest.mark.parametrize("prepare", COOKIE_STATES.values(), ids=COOKIE_STATES)
def test_every_wrong_credential_gets_the_same_answer(prepare, cause):
    fields, body = WRONG_CREDENTIALS[cause]
    account(**fields)
    reference_client = Client(enforce_csrf_checks=True)
    prepare(reference_client)
    client = Client(enforce_csrf_checks=True)
    prepare(client)

    reference = send(reference_client, {"email": OTHER_EMAIL, "password": PASSWORD})
    response = send(client, body)

    assert response.status_code == 400
    assert response.json() == CREDENTIALS_REJECTED
    assert comparable(response) == comparable(reference)


# --- Sesión -------------------------------------------------------------------

PREVIOUS_SESSIONS = {
    "anonymous": anonymous_session,
    "another-account": another_account_session,
    "same-account": same_account_session,
    "staff": staff_session,
}


@pytest.mark.parametrize(
    "prepare", PREVIOUS_SESSIONS.values(), ids=PREVIOUS_SESSIONS.keys()
)
def test_a_previous_session_is_replaced(csrf_client, prepare):
    user = account()
    old_key = prepare(csrf_client)

    response = send(csrf_client)

    assert response.status_code == 200
    new_key = response.cookies[SESSION_COOKIE].value
    assert new_key != old_key
    assert not Session.objects.filter(session_key=old_key).exists()
    decoded = Session.objects.get(session_key=new_key).get_decoded()
    assert decoded[SESSION_KEY] == str(user.pk)
    assert "basket" not in decoded
    assert response.cookies[CSRF_COOKIE].value != TOKEN


def test_an_expired_session_cookie_does_not_prevent_logging_in(csrf_client):
    account()
    key = anonymous_session(csrf_client)
    past = timezone.now() - timedelta(days=1)
    Session.objects.filter(session_key=key).update(expire_date=past)

    response = send(csrf_client)

    assert response.status_code == 200
    assert csrf_client.get(SESSION_URL).json() == {"user": {"email": EMAIL}}


def test_a_malformed_session_cookie_does_not_prevent_logging_in(csrf_client):
    account()
    short_session_cookie(csrf_client)

    response = send(csrf_client)

    assert response.status_code == 200
    assert csrf_client.get(SESSION_URL).json() == {"user": {"email": EMAIL}}


WELL_FORMED_SESSIONS = {
    "without-session": no_session,
    "anonymous": anonymous_session,
    "another-account": another_account_session,
}


@pytest.mark.parametrize(
    "prepare", WELL_FORMED_SESSIONS.values(), ids=WELL_FORMED_SESSIONS.keys()
)
def test_a_failed_login_touches_neither_the_session_nor_the_cookies(
    csrf_client, prepare
):
    account()
    key = prepare(csrf_client)
    before = stored_sessions()

    with untouchable_session_store():
        response = send(csrf_client, {"email": EMAIL, "password": WRONG_PASSWORD})

    assert response.status_code == 400
    # Con las cookies bien formadas no cambia ninguna, tampoco csrftoken
    assert not response.cookies
    assert stored_sessions() == before
    if key is not None:
        assert csrf_client.cookies[SESSION_COOKIE].value == key


def test_replacing_a_session_of_another_account_does_not_send_user_logged_out(
    csrf_client,
):
    account()
    another_account_session(csrf_client)
    received = []

    def receiver(sender, **kwargs):
        received.append(kwargs)

    user_logged_out.connect(receiver, weak=False)
    try:
        response = send(csrf_client)
    finally:
        user_logged_out.disconnect(receiver)

    assert response.status_code == 200
    assert received == []


def test_a_session_cookie_with_null_characters_gives_a_server_error_on_success():
    # Riesgo aceptado: flush() borra por esa clave y PostgreSQL rechaza el nulo
    account()
    client = Client(enforce_csrf_checks=True, raise_request_exception=False)
    # Ocho nulos escritos como escape octal, que la cookie deshace al leerla
    cookie = f'{CSRF_COOKIE}={TOKEN}; {SESSION_COOKIE}="{OCTAL_NULL * 8}"'

    response = client.post(
        URL,
        data=json.dumps(CREDENTIALS),
        content_type=JSON,
        headers={"X-CSRFToken": TOKEN},
        HTTP_COOKIE=cookie,
    )

    assert response.status_code == 500
    assert not Session.objects.exists()


# --- CSRF ---------------------------------------------------------------------

CSRF_REJECTED = {
    "no-header": {"token": None},
    "empty-header": {"token": ""},
    "no-cookie": {"cookie": None},
    "header-differs-from-cookie": {"token": OTHER_TOKEN},
}


@pytest.mark.parametrize(
    "prepare", WELL_FORMED_SESSIONS.values(), ids=WELL_FORMED_SESSIONS.keys()
)
@pytest.mark.parametrize("variant", CSRF_REJECTED.values(), ids=CSRF_REJECTED.keys())
def test_without_a_valid_token_the_credentials_are_not_checked(
    csrf_client, credentials_never_checked, prepare, variant
):
    account()
    key = prepare(csrf_client)
    before = stored_sessions()

    with untouchable_session_store():
        response = send(csrf_client, **variant)

    assert response.status_code == 403
    assert response.json() == {"code": "csrf_failed"}
    assert_no_store(response)
    assert SESSION_COOKIE not in response.cookies
    assert stored_sessions() == before
    if key is not None:
        assert csrf_client.cookies[SESSION_COOKIE].value == key


def test_a_foreign_origin_is_rejected_even_with_a_valid_token(
    csrf_client, credentials_never_checked
):
    response = send(csrf_client, HTTP_ORIGIN="http://evil.test")

    assert response.json() == {"code": "csrf_failed"}


def test_the_body_is_not_read_before_the_csrf_check(csrf_client):
    with mock.patch.object(LimitedStream, "read", side_effect=AssertionError):
        response = send(csrf_client, token=None)

    assert response.json() == {"code": "csrf_failed"}


# --- Cuerpo -------------------------------------------------------------------

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
    csrf_client, credentials_never_checked, body, extra, status, code
):
    response = send(csrf_client, body, **extra)

    assert response.status_code == status
    assert response.json() == {"code": code}
    assert_no_store(response)


def padded_body(size):
    base = json.dumps({"email": OTHER_EMAIL, "password": PASSWORD, "pad": ""})
    body = json.dumps(
        {"email": OTHER_EMAIL, "password": PASSWORD, "pad": "x" * (size - len(base))}
    )
    assert len(body.encode()) == size
    return body


def test_a_body_of_4096_bytes_is_read_and_one_of_4097_is_too_large(csrf_client):
    assert send(csrf_client, padded_body(MAX_BYTES)).json() == CREDENTIALS_REJECTED

    response = send(csrf_client, padded_body(MAX_BYTES + 1))

    assert response.status_code == 413
    assert response.json() == {"code": "payload_too_large"}


def test_a_body_that_is_not_json_is_an_invalid_request(
    csrf_client, credentials_never_checked
):
    csrf_client.cookies[CSRF_COOKIE] = TOKEN

    response = csrf_client.post(
        URL,
        data=json.dumps(CREDENTIALS),
        content_type="text/plain",
        headers={"X-CSRFToken": TOKEN},
    )

    assert response.json() == {"code": "invalid_request"}


def test_privileged_fields_and_next_are_ignored(csrf_client):
    user = account()
    body = {
        **CREDENTIALS,
        "is_staff": True,
        "is_superuser": True,
        "is_active": False,
        "next": "https://otro.sitio/",
    }

    response = send(csrf_client, body)

    assert response.status_code == 200
    assert response.json() == {"user": {"email": EMAIL}}
    assert "Location" not in response
    user.refresh_from_db()
    assert (user.is_staff, user.is_superuser, user.is_active) == (False, False, True)


# --- Métodos ------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete", "options", "head"])
def test_every_other_method_gets_405_with_allow_post(
    csrf_client, credentials_never_checked, method
):
    response = send(csrf_client, method=method, token=None)

    assert response.status_code == 405
    assert response["Allow"] == "POST"
    assert_no_store(response)
    if method != "head":
        assert response.json() == {"code": "method_not_allowed"}


# --- Caché, origen cruzado y respuestas mínimas -------------------------------

EVERY_ANSWER = {
    "200": (send, 200),
    "400-invalid-fields": (
        lambda c: send(c, {"email": EMAIL, "password": WRONG_PASSWORD}),
        400,
    ),
    "400-invalid-request": (lambda c: send(c, "[]"), 400),
    "403": (lambda c: send(c, token=None), 403),
    "405": (lambda c: send(c, method="put"), 405),
    "413": (lambda c: send(c, "{" + " " * 5000 + "}"), 413),
    "429-ip-limit": (ip_limited_answer, 429),
    "429-pair-limit": (pair_limited_answer, 429),
}


@pytest.mark.parametrize(("send_it", "status"), EVERY_ANSWER.values(), ids=EVERY_ANSWER)
def test_no_answer_can_be_stored_by_a_cache(csrf_client, send_it, status):
    account()

    response = send_it(csrf_client)

    assert response.status_code == status
    assert_no_store(response)


@pytest.mark.parametrize(("send_it", "status"), EVERY_ANSWER.values(), ids=EVERY_ANSWER)
def test_no_answer_grants_cross_origin_access(csrf_client, send_it, status):
    account()

    response = send_it(csrf_client)

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


@pytest.mark.parametrize(
    ("send_it", "keys"),
    [
        (
            lambda c: send(c, {"email": EMAIL, "password": WRONG_PASSWORD}),
            {"code", "params"},
        ),
        (lambda c: send(c, "[]"), {"code"}),
        (lambda c: send(c, token=None), {"code"}),
        (lambda c: send(c, method="put"), {"code"}),
        (ip_limited_answer, {"code", "retry_after"}),
        (pair_limited_answer, {"code", "retry_after"}),
    ],
    ids=[
        "invalid-fields",
        "invalid-request",
        "csrf-failed",
        "method-not-allowed",
        "ip-throttled",
        "pair-throttled",
    ],
)
def test_errors_carry_only_their_planned_keys(csrf_client, send_it, keys):
    account()
    staff_session(csrf_client)

    response = send_it(csrf_client)

    assert set(response.json()) == keys
    assert "staff@correo.es" not in response.content.decode()


# --- Límite por IP ------------------------------------------------------------


def test_the_twenty_first_login_from_one_ip_is_throttled_before_the_credentials(
    csrf_client, monkeypatch
):
    account()
    for _ in range(IP_LIMIT):
        assert send(csrf_client).status_code == 200
    forbid_credential_checks(monkeypatch)
    before = stored_sessions()

    with untouchable_session_store():
        response = send(csrf_client)

    assert assert_throttled(response) == MINUTE
    assert SESSION_COOKIE not in response.cookies
    assert stored_sessions() == before


def test_a_pair_rejection_counts_towards_the_ip_limit(csrf_client):
    account()
    account(OTHER_EMAIL)
    fail(csrf_client)
    for _ in range(IP_LIMIT - PAIR_LIMIT):
        assert assert_throttled(send(csrf_client)) == PAIR_WAIT

    response = send(csrf_client, {"email": OTHER_EMAIL, "password": PASSWORD})

    assert assert_throttled(response) == MINUTE


@pytest.mark.parametrize(
    "method", ["get", "put", "patch", "delete", "options", "head", "post"]
)
def test_once_the_ip_limit_is_reached_every_method_gets_429(csrf_client, method):
    reject_by_csrf(csrf_client)

    response = send(csrf_client, method=method, token=None)

    # HEAD no lleva cuerpo: solo el estado y la cabecera
    if method == "head":
        assert response.status_code == 429
        assert response["Retry-After"] == str(MINUTE)
    else:
        assert assert_throttled(response) == MINUTE


def test_a_different_x_forwarded_for_on_each_request_does_not_avoid_the_ip_limit(
    csrf_client,
):
    account()
    for index in range(IP_LIMIT):
        forwarded = f"198.51.100.{index}"
        assert send(csrf_client, HTTP_X_FORWARDED_FOR=forwarded).status_code == 200

    response = send(csrf_client, HTTP_X_FORWARDED_FOR="198.51.100.200")

    assert assert_throttled(response) == MINUTE


# --- Límite del par IP y email ------------------------------------------------


def test_five_failures_throttle_the_correct_password_without_checking_it(
    csrf_client, monkeypatch
):
    account()
    fail(csrf_client)
    forbid_credential_checks(monkeypatch)
    before = stored_sessions()

    with untouchable_session_store():
        response = send(csrf_client)

    assert assert_throttled(response) == PAIR_WAIT
    assert SESSION_COOKIE not in response.cookies
    assert stored_sessions() == before


def test_the_pair_wait_counts_from_the_fifth_most_recent_failure(csrf_client, clock):
    account()
    # Siete fallos, del más reciente al más antiguo: el quinto fue hace 50 s
    marks = [clock.now - seconds for seconds in range(10, 80, 10)]
    key = login_pair_key(LOCAL_BUCKET, EMAIL)
    caches[LOGIN_CACHE_ALIAS].set(key, marks, PAIR_WAIT)

    response = send(csrf_client)

    assert assert_throttled(response) == PAIR_WAIT - 50


def test_fifteen_minutes_after_the_first_failure_the_account_can_log_in(
    csrf_client, clock
):
    account()
    first = clock.now
    for _ in range(PAIR_LIMIT):
        fail(csrf_client, times=1)
        clock.advance(1)

    clock.now = first + PAIR_WAIT - 1
    assert assert_throttled(send(csrf_client)) == 1
    clock.now = first + PAIR_WAIT
    assert send(csrf_client).status_code == 200


def test_a_success_does_not_reset_the_failures(csrf_client):
    account()
    fail(csrf_client, times=PAIR_LIMIT - 1)
    assert send(csrf_client).status_code == 200
    fail(csrf_client, times=1)

    # Séptima petición: la sexta fue el quinto fallo
    response = send(csrf_client)

    assert assert_throttled(response) == PAIR_WAIT


def test_a_success_is_not_counted_as_a_failure(csrf_client):
    account()
    fail(csrf_client, times=PAIR_LIMIT - 1)

    assert send(csrf_client).status_code == 200
    assert send(csrf_client).status_code == 200


def test_pair_rejections_are_not_counted_as_failures(csrf_client, clock):
    account()
    start = clock.now
    fail(csrf_client)
    clock.now = start + 100
    for _ in range(PAIR_LIMIT):
        assert assert_throttled(send(csrf_client)) == PAIR_WAIT - 100

    # Si los rechazos contaran, seguiría bloqueada hasta 100 s después
    clock.now = start + PAIR_WAIT
    assert send(csrf_client).status_code == 200


UNQUERYABLE_EMAILS = {
    "absent": {"password": WRONG_PASSWORD},
    "null": {"email": None, "password": WRONG_PASSWORD},
    "empty": {"email": "", "password": WRONG_PASSWORD},
    "blank": {"email": "   ", "password": WRONG_PASSWORD},
    "null-character": {
        "email": f"ana{NULL_CHARACTER}@correo.es",
        "password": WRONG_PASSWORD,
    },
    "lone-surrogate": {
        "email": f"ana{SURROGATE}@correo.es",
        "password": WRONG_PASSWORD,
    },
}


@pytest.mark.parametrize(
    "body", UNQUERYABLE_EMAILS.values(), ids=UNQUERYABLE_EMAILS.keys()
)
def test_failures_with_an_email_that_cannot_be_queried_count(csrf_client, body):
    account()
    fail(csrf_client, body)

    response = send(csrf_client, body)

    assert assert_throttled(response) == PAIR_WAIT


@pytest.mark.parametrize(
    ("failing_address", "other_address"),
    [
        ("203.0.113.7", "203.0.113.8"),
        ("2001:db8:0:1::1", "2001:db8:0:2::1"),
    ],
    ids=["ipv4", "ipv6-other-64"],
)
def test_the_same_email_from_another_network_can_log_in(
    csrf_client, failing_address, other_address
):
    account()
    fail(csrf_client, REMOTE_ADDR=failing_address)

    response = send(csrf_client, REMOTE_ADDR=other_address)

    assert response.status_code == 200


def test_two_addresses_of_the_same_ipv6_64_share_the_pair_limit(csrf_client):
    account()
    fail(csrf_client, REMOTE_ADDR="2001:db8:0:1::1")

    response = send(csrf_client, REMOTE_ADDR="2001:db8:0:1:ffff::1")

    assert assert_throttled(response) == PAIR_WAIT


def test_a_different_x_forwarded_for_on_each_request_does_not_avoid_the_pair_limit(
    csrf_client,
):
    account()
    for index in range(PAIR_LIMIT):
        fail(csrf_client, times=1, HTTP_X_FORWARDED_FOR=f"198.51.100.{index}")

    response = send(csrf_client, HTTP_X_FORWARDED_FOR="198.51.100.200")

    assert assert_throttled(response) == PAIR_WAIT


# --- Orden de comprobaciones --------------------------------------------------

LIMITS = {"ip": (reject_by_csrf, MINUTE), "pair": (fail, PAIR_WAIT)}


@pytest.mark.parametrize(
    "prepare", WELL_FORMED_SESSIONS.values(), ids=WELL_FORMED_SESSIONS.keys()
)
@pytest.mark.parametrize(("reach_the_limit", "wait"), LIMITS.values(), ids=LIMITS)
def test_a_throttled_login_touches_neither_the_session_nor_the_cookies(
    csrf_client, reach_the_limit, wait, prepare
):
    account()
    key = prepare(csrf_client)
    reach_the_limit(csrf_client)
    before = stored_sessions()

    with untouchable_session_store():
        response = send(csrf_client)

    assert assert_throttled(response) == wait
    assert not response.cookies
    assert stored_sessions() == before
    if key is not None:
        assert csrf_client.cookies[SESSION_COOKIE].value == key


def send_as_text_plain(client, body):
    client.cookies[CSRF_COOKIE] = TOKEN
    return client.post(
        URL,
        data=json.dumps(body),
        content_type="text/plain",
        headers={"X-CSRFToken": TOKEN},
    )


# (envío con el email y la contraseña errónea cuando la forma lo permite, estado)
REJECTED_BEFORE_THE_CREDENTIALS = {
    "no-header": (lambda c: send(c, WRONG_PASSWORD_BODY, token=None), 403),
    "empty-header": (lambda c: send(c, WRONG_PASSWORD_BODY, token=""), 403),
    "no-cookie": (lambda c: send(c, WRONG_PASSWORD_BODY, cookie=None), 403),
    "header-differs": (lambda c: send(c, WRONG_PASSWORD_BODY, token=OTHER_TOKEN), 403),
    "foreign-origin": (
        lambda c: send(c, WRONG_PASSWORD_BODY, HTTP_ORIGIN=FOREIGN_ORIGIN),
        403,
    ),
    "put": (lambda c: send(c, WRONG_PASSWORD_BODY, method="put"), 405),
    "patch": (lambda c: send(c, WRONG_PASSWORD_BODY, method="patch"), 405),
    "delete": (lambda c: send(c, WRONG_PASSWORD_BODY, method="delete"), 405),
    "text-plain": (lambda c: send_as_text_plain(c, WRONG_PASSWORD_BODY), 400),
    "email-number": (
        lambda c: send(c, {"email": 5, "password": WRONG_PASSWORD}),
        400,
    ),
    "too-large-declared": (
        lambda c: send(c, json.dumps(WRONG_PASSWORD_BODY) + " " * MAX_BYTES),
        413,
    ),
    "chunked": (
        lambda c: send(c, WRONG_PASSWORD_BODY, HTTP_TRANSFER_ENCODING="chunked"),
        413,
    ),
    "4097-bytes": (lambda c: send(c, padded_body(MAX_BYTES + 1)), 413),
}


def stored_pair_keys():
    return [key for key in caches[LOGIN_CACHE_ALIAS]._cache if "login_pair:" in key]


@pytest.mark.parametrize(
    ("reject", "status"),
    REJECTED_BEFORE_THE_CREDENTIALS.values(),
    ids=REJECTED_BEFORE_THE_CREDENTIALS.keys(),
)
def test_no_rejection_before_the_credentials_records_a_failure(
    csrf_client, reject, status
):
    account()
    for _ in range(PAIR_LIMIT):
        assert reject(csrf_client).status_code == status

    assert stored_pair_keys() == []
    assert send(csrf_client).status_code == 200


PAIR_BLOCKED_REJECTIONS = {
    **MALFORMED,
    "no-csrf-header": (None, {"token": None}, 403, "csrf_failed"),
    "foreign-origin": (None, {"HTTP_ORIGIN": FOREIGN_ORIGIN}, 403, "csrf_failed"),
    "put": (None, {"method": "put"}, 405, "method_not_allowed"),
}


@pytest.mark.parametrize(
    ("body", "extra", "status", "code"),
    PAIR_BLOCKED_REJECTIONS.values(),
    ids=PAIR_BLOCKED_REJECTIONS.keys(),
)
def test_with_the_pair_blocked_each_earlier_rejection_gets_its_own_error(
    csrf_client, monkeypatch, body, extra, status, code
):
    account()
    fail(csrf_client)
    fail(csrf_client, {"password": WRONG_PASSWORD})
    limit = LoginFailureLimit()
    assert limit.wait(login_pair_key(LOCAL_BUCKET, EMAIL)) == PAIR_WAIT
    assert limit.wait(login_pair_key(LOCAL_BUCKET, None)) == PAIR_WAIT
    forbid_credential_checks(monkeypatch)

    response = send(csrf_client, body, **extra)

    assert response.status_code == status
    assert response.json() == {"code": code}
    if status == 405:
        assert response["Allow"] == "POST"


# --- Fugas --------------------------------------------------------------------


def test_no_answer_log_or_limit_store_contains_the_email_or_the_password(
    csrf_client, caplog, monkeypatch
):
    # Condición previa: con el SQL en DEBUG la consulta llevaría el email
    backends = logging.getLogger("django.db.backends")
    assert backends.getEffectiveLevel() >= logging.INFO
    assert connection.force_debug_cursor is False
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(connection, "force_debug_cursor", True)
    email = f"{MARK}.ana@correo.es"
    correct = {"email": email, "password": f"{MARK} vela roja en el puerto"}
    wrong = {"email": email, "password": f"{MARK} vela azul en el puerto"}
    account(**correct)
    failed_logins = []

    def receiver(sender, credentials, **kwargs):
        failed_logins.append(credentials)

    user_login_failed.connect(receiver, weak=False)
    try:
        responses = [send(csrf_client, correct)]
        responses += [send(csrf_client, wrong) for _ in range(PAIR_LIMIT)]
        # Rechazos del par hasta agotar el límite por IP, y uno más
        pair_rejections = IP_LIMIT - 1 - PAIR_LIMIT
        responses += [send(csrf_client, correct) for _ in range(pair_rejections)]
        responses.append(send(csrf_client, correct))
    finally:
        user_login_failed.disconnect(receiver)

    statuses = [response.status_code for response in responses]
    assert statuses == [200] + [400] * PAIR_LIMIT + [429] * (pair_rejections + 1)
    assert assert_throttled(responses[PAIR_LIMIT + 1]) == PAIR_WAIT
    assert assert_throttled(responses[-1]) == MINUTE
    assert [r for r in caplog.records if r.name == "django.request"]
    assert MARK not in caplog.text.lower()
    # El cuerpo del acierto lleva el email por contrato; el de los rechazos, no
    for response in responses[1:]:
        assert MARK not in response.content.decode().lower()
    for response in responses:
        assert MARK not in repr(dict(response.headers.items())).lower()
        assert MARK not in response.cookies.output().lower()
    stored = caches[LOGIN_CACHE_ALIAS]._cache
    assert stored_pair_keys()
    for key, value in stored.items():
        assert MARK not in key.lower()
        assert MARK.encode() not in value.lower()
    assert MARK not in repr(django_settings.CACHES).lower()
    assert len(failed_logins) == PAIR_LIMIT
    assert all(credentials["password"] == HIDDEN for credentials in failed_logins)


def test_the_error_report_hides_the_body_fields_in_the_login_view(
    csrf_client, settings, monkeypatch
):
    # El filtro de Django solo tapa con DEBUG desactivado
    settings.DEBUG = False

    def explode(*args, **kwargs):
        raise RuntimeError("credentials check failed")

    monkeypatch.setattr(views, "check_credentials", explode)
    body = {"email": f"{MARK}.ana@correo.es", "password": f"{MARK} vela roja"}

    with pytest.raises(RuntimeError) as raised:
        send(csrf_client, body)

    reporter = ExceptionReporter(None, raised.type, raised.value, raised.tb)
    # El cliente de pruebas también tiene un marco post, y lleva el cuerpo en claro
    frame = next(
        frame
        for frame in reporter.get_traceback_frames()
        if frame["function"] == "post"
        and frame["filename"].endswith("apps/users/views.py")
    )
    shown = dict(frame["vars"])
    assert shown["fields"] == HIDDEN
    assert MARK not in repr(frame["vars"]).lower()
