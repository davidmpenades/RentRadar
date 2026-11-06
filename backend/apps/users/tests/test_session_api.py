import re
from datetime import timedelta

import pytest
from django.conf import settings as django_settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.cache import cc_delim_re

from apps.users.models import User
from apps.users.tests.helpers import assert_no_store

pytestmark = pytest.mark.django_db

URL = "/api/v1/auth/session/"
REGISTER_URL = "/api/v1/auth/register/"
JSON = "application/json"
EMAIL = "ana@correo.es"
PASSWORD = "vela roja en el puerto"
TOKEN = "a1B2c3D4" * 4
SESSION_COOKIE = django_settings.SESSION_COOKIE_NAME
CSRF_COOKIE = django_settings.CSRF_COOKIE_NAME
# Formato válido de clave de sesión, sin fila en la BD
KEY_WITHOUT_ROW = "k3y5in4f1l4" * 3


def who_am_i(client, method="get", **extra):
    return getattr(client, method)(URL, **extra)


def log_in(client, **fields):
    user = User.objects.create(email=EMAIL, **fields)
    client.force_login(user)
    return user, client.cookies[SESSION_COOKIE].value


def vary_tokens(response):
    return {token.strip().lower() for token in cc_delim_re.split(response["Vary"])}


def assert_varies_by_cookie(response):
    assert "cookie" in vary_tokens(response)


def assert_session_cookie_deleted(response):
    cookie = response.cookies[SESSION_COOKIE]
    assert cookie.value == ""
    assert cookie["max-age"] == 0


# --- Estados de la sesión que llega en la petición -----------------------------


def no_session(client):
    return None


def valid_session(client):
    return log_in(client)[1]


def deactivated_account(client):
    user, key = log_in(client)
    user.is_active = False
    user.save(update_fields=["is_active"])
    return key


def expired_session(client):
    key = valid_session(client)
    past = timezone.now() - timedelta(seconds=1)
    Session.objects.filter(session_key=key).update(expire_date=past)
    return key


def short_cookie(client):
    # Django descarta sin consultar la BD una clave de menos de 8 caracteres
    client.cookies[SESSION_COOKIE] = "abc1234"
    return "abc1234"


def long_malformed_cookie(client):
    value = "no-es-una-clave-de-sesion-" * 3
    client.cookies[SESSION_COOKIE] = value
    return value


def key_without_row(client):
    client.cookies[SESSION_COOKIE] = KEY_WITHOUT_ROW
    return KEY_WITHOUT_ROW


EMPTY_SESSIONS = pytest.mark.parametrize(
    "prepare",
    [expired_session, short_cookie, long_malformed_cookie, key_without_row],
    ids=["expired", "shorter-than-8", "long-malformed", "key-without-row"],
)

EVERY_STATE = pytest.mark.parametrize(
    "prepare",
    [
        no_session,
        valid_session,
        deactivated_account,
        expired_session,
        short_cookie,
        long_malformed_cookie,
        key_without_row,
    ],
    ids=[
        "without-session",
        "valid",
        "deactivated",
        "expired",
        "shorter-than-8",
        "long-malformed",
        "key-without-row",
    ],
)


# --- Respuesta ----------------------------------------------------------------


def test_an_anonymous_visitor_gets_a_null_user_and_a_csrf_cookie(csrf_client):
    response = who_am_i(csrf_client)

    assert response.status_code == 200
    assert response.json() == {"user": None}
    cookie = response.cookies[CSRF_COOKIE]
    assert re.fullmatch(r"[A-Za-z0-9]{32}", cookie.value)
    assert not cookie["httponly"]
    assert SESSION_COOKIE not in response.cookies


def test_a_valid_session_gets_its_email_and_keeps_its_cookie(csrf_client):
    key = valid_session(csrf_client)

    response = who_am_i(csrf_client)

    assert response.status_code == 200
    assert response.json() == {"user": {"email": EMAIL}}
    assert SESSION_COOKIE not in response.cookies
    assert csrf_client.cookies[SESSION_COOKIE].value == key


def test_after_a_real_registration_the_session_answers_with_its_email(csrf_client):
    # El token sale de «quién soy», como en el navegador
    token = who_am_i(csrf_client).cookies[CSRF_COOKIE].value
    registered = csrf_client.post(
        REGISTER_URL,
        data={"email": "  Ana@Correo.ES ", "password": PASSWORD},
        content_type=JSON,
        headers={"X-CSRFToken": token},
    )
    assert registered.status_code == 201

    response = who_am_i(csrf_client)

    assert response.json() == {"user": {"email": EMAIL}}


def test_a_deactivated_account_gets_a_null_user_and_keeps_its_session(csrf_client):
    key = deactivated_account(csrf_client)

    response = who_am_i(csrf_client)

    assert response.status_code == 200
    assert response.json() == {"user": None}
    assert SESSION_COOKIE not in response.cookies
    assert Session.objects.filter(session_key=key).exists()
    assert csrf_client.cookies[SESSION_COOKIE].value == key


@EMPTY_SESSIONS
def test_an_expired_malformed_or_unknown_session_is_null_and_its_cookie_deleted(
    csrf_client, prepare
):
    prepare(csrf_client)

    response = who_am_i(csrf_client)

    assert response.status_code == 200
    assert response.json() == {"user": None}
    assert_session_cookie_deleted(response)


@EVERY_STATE
@pytest.mark.parametrize("method", ["get", "head"])
def test_every_answer_is_not_stored_varies_by_cookie_and_sets_the_csrf_cookie(
    csrf_client, prepare, method
):
    prepare(csrf_client)

    response = who_am_i(csrf_client, method)

    assert response.status_code == 200
    assert_no_store(response)
    assert_varies_by_cookie(response)
    assert response.cookies[CSRF_COOKIE].value


def test_head_answers_without_a_body(csrf_client):
    valid_session(csrf_client)

    response = who_am_i(csrf_client, "head")

    assert response.status_code == 200
    assert response.content == b""


def test_asking_does_not_renew_the_session(csrf_client):
    key = valid_session(csrf_client)
    expiry = timezone.now() + timedelta(days=1)
    Session.objects.filter(session_key=key).update(expire_date=expiry)

    for method in ("get", "head", "get"):
        assert who_am_i(csrf_client, method).status_code == 200

    assert Session.objects.get(session_key=key).expire_date == expiry


def test_a_staff_session_gets_only_its_email(csrf_client):
    log_in(csrf_client, is_staff=True, is_superuser=True)

    response = who_am_i(csrf_client)

    body = response.json()
    assert list(body) == ["user"]
    assert list(body["user"]) == ["email"]
    assert body["user"]["email"] == EMAIL
    text = response.content.decode()
    for hidden in ("id", "staff", "superuser", "last_login", "date_joined", "active"):
        assert hidden not in text


# --- Métodos no admitidos -----------------------------------------------------


def session_without_token(client):
    valid_session(client)
    return {}


def session_with_a_valid_token(client):
    valid_session(client)
    client.cookies[CSRF_COOKIE] = TOKEN
    return {"X-CSRFToken": TOKEN}


def without_session(client):
    return {}


@pytest.mark.parametrize(
    "prepare",
    [session_without_token, session_with_a_valid_token, without_session],
    ids=["session-without-token", "session-with-valid-token", "without-session"],
)
@pytest.mark.parametrize("method", ["post", "put", "patch", "delete", "options"])
def test_every_other_method_gets_405_before_authenticating(
    csrf_client, prepare, method
):
    # Con sesión y sin token, autenticar antes daría el 403 de CSRF
    headers = prepare(csrf_client)

    response = who_am_i(csrf_client, method, headers=headers)

    assert response.status_code == 405
    assert response.json() == {"code": "method_not_allowed"}
    assert response["Allow"] == "GET, HEAD"
    assert_no_store(response)
    assert CSRF_COOKIE not in response.cookies
    assert SESSION_COOKIE not in response.cookies
