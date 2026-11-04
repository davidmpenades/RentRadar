from contextlib import ExitStack, contextmanager
from datetime import timedelta
from unittest import mock

import pytest
from django.conf import settings as django_settings
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.handlers.wsgi import LimitedStream
from django.test import Client
from django.utils import timezone

from apps.users.models import User
from apps.users.tests.helpers import assert_no_store

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/logout/"
SESSION_URL = "/api/v1/auth/session/"
JSON = "application/json"
EMAIL = "ana@correo.es"
TOKEN = "a1B2c3D4" * 4
OTHER_TOKEN = "z9Y8x7W6" * 4
SESSION_COOKIE = django_settings.SESSION_COOKIE_NAME
CSRF_COOKIE = django_settings.CSRF_COOKIE_NAME
# Formato válido de clave de sesión, sin fila en la BD
KEY_WITHOUT_ROW = "k3y5in4f1l4" * 3


def logout(client, *, token=TOKEN, cookie=TOKEN, method="post", body="", **extra):
    if cookie is not None:
        client.cookies[CSRF_COOKIE] = cookie
    headers = {} if token is None else {"X-CSRFToken": token}
    # Sin cuerpo, como lo envía el navegador
    return client.generic(
        method.upper(), URL, data=body, content_type=JSON, headers=headers, **extra
    )


def log_in(client, email=EMAIL, **fields):
    user = User.objects.create(email=email, **fields)
    client.force_login(user)
    return client.cookies[SESSION_COOKIE].value


def stored_sessions():
    return list(
        Session.objects.order_by("session_key").values_list(
            "session_key", "session_data", "expire_date"
        )
    )


def stored_accounts():
    return list(
        User.objects.order_by("pk").values_list(
            "pk", "email", "password", "is_active", "is_staff", "last_login"
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


def cross_origin_headers(response):
    return [n for n in response.headers if n.lower().startswith("access-control-")]


def assert_session_cookie_deleted(response):
    cookie = response.cookies[SESSION_COOKIE]
    assert cookie.value == ""
    assert cookie["max-age"] == 0


def assert_logged_out(response):
    assert response.status_code == 204
    assert response.content == b""
    assert_session_cookie_deleted(response)
    assert_no_store(response)


def who_am_i(client):
    return client.get(SESSION_URL).json()


# --- Con sesión ---------------------------------------------------------------


def test_logging_out_destroys_the_session_row(csrf_client):
    key = log_in(csrf_client)

    response = logout(csrf_client)

    assert_logged_out(response)
    assert "Content-Type" not in response
    assert not Session.objects.filter(session_key=key).exists()


def test_the_previous_identifier_no_longer_authenticates(csrf_client):
    key = log_in(csrf_client)
    assert who_am_i(csrf_client) == {"user": {"email": EMAIL}}

    logout(csrf_client)
    csrf_client.cookies[SESSION_COOKIE] = key

    assert who_am_i(csrf_client) == {"user": None}


def test_only_the_session_of_the_cookie_is_closed(csrf_client):
    log_in(csrf_client)
    other = Client()
    other_key = log_in(other, "luis@correo.es")

    logout(csrf_client)

    assert Session.objects.filter(session_key=other_key).exists()
    assert who_am_i(other) == {"user": {"email": "luis@correo.es"}}


def test_the_csrf_cookie_is_left_untouched(csrf_client):
    log_in(csrf_client)

    response = logout(csrf_client)

    assert response.status_code == 204
    assert CSRF_COOKIE not in response.cookies
    assert csrf_client.cookies[CSRF_COOKIE].value == TOKEN


def test_an_expired_session_row_is_deleted_too(csrf_client):
    key = log_in(csrf_client)
    past = timezone.now() - timedelta(seconds=1)
    Session.objects.filter(session_key=key).update(expire_date=past)

    response = logout(csrf_client)

    assert_logged_out(response)
    assert not Session.objects.filter(session_key=key).exists()


# --- Sin sesión válida --------------------------------------------------------


def short_cookie(client):
    client.cookies[SESSION_COOKIE] = "abc1234"


def long_malformed_cookie(client):
    client.cookies[SESSION_COOKIE] = "no-es-una-clave-de-sesion-" * 3


def key_without_row(client):
    # La sesión ya se cerró en otra pestaña
    client.cookies[SESSION_COOKIE] = KEY_WITHOUT_ROW


def no_session_cookie(client):
    pass


WITHOUT_A_VALID_SESSION = pytest.mark.parametrize(
    "prepare",
    [short_cookie, long_malformed_cookie, key_without_row, no_session_cookie],
    ids=["shorter-than-8", "long-malformed", "closed-in-another-tab", "no-cookie"],
)


@WITHOUT_A_VALID_SESSION
def test_without_a_valid_session_it_answers_204_and_removes_the_cookie(
    csrf_client, prepare
):
    prepare(csrf_client)

    assert_logged_out(logout(csrf_client))


@WITHOUT_A_VALID_SESSION
def test_without_a_valid_session_nothing_else_changes(csrf_client, prepare):
    log_in(Client(), "luis@correo.es")
    anonymous = SessionStore()
    anonymous["basket"] = "kept"
    anonymous.create()
    sessions, accounts = stored_sessions(), stored_accounts()
    prepare(csrf_client)

    assert logout(csrf_client).status_code == 204
    assert stored_sessions() == sessions
    assert stored_accounts() == accounts


COOKIE_SETTINGS = {
    "project-settings": {},
    "other-path-domain-and-samesite": {
        "SESSION_COOKIE_PATH": "/api/",
        "SESSION_COOKIE_DOMAIN": "rentradar.test",
        "SESSION_COOKIE_SAMESITE": "Strict",
    },
}


@pytest.mark.parametrize(
    "overrides", COOKIE_SETTINGS.values(), ids=COOKIE_SETTINGS.keys()
)
def test_without_a_session_cookie_the_view_deletes_it_with_its_settings(
    csrf_client, settings, overrides
):
    # Con la cookie en la petición, SessionMiddleware pisaría la cabecera de la vista
    for name, value in overrides.items():
        setattr(settings, name, value)

    response = logout(csrf_client)

    cookie = response.cookies[SESSION_COOKIE]
    assert cookie.value == ""
    assert cookie["max-age"] == 0
    assert cookie["expires"] == "Thu, 01 Jan 1970 00:00:00 GMT"
    assert cookie["path"] == settings.SESSION_COOKIE_PATH
    assert cookie["domain"] == (settings.SESSION_COOKIE_DOMAIN or "")
    assert cookie["samesite"] == settings.SESSION_COOKIE_SAMESITE


# --- CSRF ---------------------------------------------------------------------

CSRF_REJECTED = {
    "no-header": {"token": None},
    "empty-header": {"token": ""},
    "no-cookie": {"cookie": None},
    "header-differs-from-cookie": {"token": OTHER_TOKEN},
}


def with_session(client):
    return log_in(client)


def without_session(client):
    return None


SESSIONS = pytest.mark.parametrize(
    "prepare", [without_session, with_session], ids=["without-session", "with-session"]
)


@SESSIONS
@pytest.mark.parametrize("variant", CSRF_REJECTED.values(), ids=CSRF_REJECTED.keys())
def test_without_a_valid_token_nothing_changes(csrf_client, prepare, variant):
    key = prepare(csrf_client)
    sessions, accounts = stored_sessions(), stored_accounts()

    with untouchable_session_store():
        response = logout(csrf_client, **variant)

    assert response.status_code == 403
    assert response.json() == {"code": "csrf_failed"}
    assert_no_store(response)
    assert SESSION_COOKIE not in response.cookies
    assert stored_sessions() == sessions
    assert stored_accounts() == accounts
    if key is not None:
        assert csrf_client.cookies[SESSION_COOKIE].value == key


@SESSIONS
def test_the_body_is_not_read_before_the_csrf_check(csrf_client, prepare):
    prepare(csrf_client)

    with mock.patch.object(LimitedStream, "read", side_effect=AssertionError):
        response = logout(csrf_client, token=None, body='{"x": 1}')

    assert response.json() == {"code": "csrf_failed"}


def test_a_foreign_origin_is_rejected_even_with_a_valid_token(csrf_client):
    key = log_in(csrf_client)

    response = logout(csrf_client, HTTP_ORIGIN="http://evil.test")

    assert response.json() == {"code": "csrf_failed"}
    assert Session.objects.filter(session_key=key).exists()


# --- Métodos ------------------------------------------------------------------


@SESSIONS
@pytest.mark.parametrize("method", ["get", "put", "patch", "delete", "options", "head"])
def test_every_other_method_gets_405_with_allow_post(csrf_client, prepare, method):
    key = prepare(csrf_client)

    response = logout(csrf_client, method=method, token=None)

    assert response.status_code == 405
    assert response["Allow"] == "POST"
    assert_no_store(response)
    if method != "head":
        assert response.json() == {"code": "method_not_allowed"}
    if key is not None:
        assert Session.objects.filter(session_key=key).exists()


# --- Caché, respuestas mínimas y orígenes -------------------------------------

EVERY_ANSWER = {
    "204": (lambda c: logout(c), 204),
    "403": (lambda c: logout(c, token=None), 403),
    "405": (lambda c: logout(c, method="put"), 405),
}


@SESSIONS
@pytest.mark.parametrize(("send", "status"), EVERY_ANSWER.values(), ids=EVERY_ANSWER)
def test_no_answer_can_be_stored_or_grants_cross_origin_access(
    csrf_client, prepare, send, status
):
    prepare(csrf_client)

    response = send(csrf_client)

    assert response.status_code == status
    assert_no_store(response)
    assert not cross_origin_headers(response)


def test_a_preflight_from_another_origin_gets_405_without_cross_origin_headers(
    csrf_client,
):
    response = csrf_client.options(
        URL,
        headers={
            "Origin": "http://evil.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-csrftoken",
        },
    )

    assert response.status_code == 405
    assert not cross_origin_headers(response)


@pytest.mark.parametrize(
    "send",
    [lambda c: logout(c, token=None), lambda c: logout(c, method="put")],
    ids=["csrf-failed", "method-not-allowed"],
)
def test_errors_carry_only_their_code_even_with_a_staff_session(csrf_client, send):
    log_in(csrf_client, "staff@correo.es", is_staff=True, is_superuser=True)

    response = send(csrf_client)

    assert set(response.json()) == {"code"}
    assert "staff@correo.es" not in response.content.decode()


def test_the_success_has_no_body_even_with_a_staff_session(csrf_client):
    log_in(csrf_client, "staff@correo.es", is_staff=True, is_superuser=True)

    response = logout(csrf_client)

    assert response.status_code == 204
    assert response.content == b""
