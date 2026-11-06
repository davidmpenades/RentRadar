import pytest
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.users.models import User

pytestmark = pytest.mark.django_db

URL = "/api/v1/public/assets/"
# Madrid: donde make_asset deja la ubicación pública del bien
MADRID_QUERY = {"south": "40.3", "west": "-3.8", "north": "40.5", "east": "-3.6"}
# Con el formato de una clave real pero sin fila en la tabla de sesiones
UNKNOWN_KEY = "a" * 32


@pytest.fixture
def member(db):
    return User.objects.create(email="member@correo.es")


@pytest.fixture
def listed_asset(make_asset):
    make_asset(status="active", title="Taladro de prueba").save()


def sql_of(captured):
    return [query["sql"] for query in captured.captured_queries]


def fetch_with_cookie(session_key):
    client = Client()
    client.cookies[settings.SESSION_COOKIE_NAME] = session_key
    with CaptureQueriesContext(connection) as captured:
        response = client.get(URL, MADRID_QUERY)
    return response, sql_of(captured)


def anonymous_answer():
    with CaptureQueriesContext(connection) as captured:
        response = Client().get(URL, MADRID_QUERY)
    return response, sql_of(captured)


def valid_session_key(member):
    client = Client()
    client.force_login(member)
    key = client.cookies[settings.SESSION_COOKIE_NAME].value
    # Condición previa: la cookie corresponde a una sesión viva de un usuario activo
    stored = SessionStore(session_key=key)
    assert stored.exists(key)
    assert stored.get("_auth_user_id") == str(member.pk)
    assert member.is_active
    return key


def expired_session_key(member):
    key = valid_session_key(member)
    Session.objects.filter(session_key=key).update(
        expire_date=timezone.now() - timezone.timedelta(days=1)
    )
    return key


def assert_never_authenticates(sql):
    # La lista une con users_user para filtrar al propietario; la sesión y el
    # usuario de la petición serían consultas aparte, sin assets_asset
    assert not [query for query in sql if "django_session" in query]
    assert not [query for query in sql if "assets_asset" not in query]


def assert_same_as_anonymous(response, baseline):
    assert response.status_code == baseline.status_code == 200
    assert response.content == baseline.content
    assert dict(response.headers) == dict(baseline.headers)
    assert not response.cookies
    assert "Set-Cookie" not in response.headers
    assert "cookie" not in response.headers.get("Vary", "").lower()


def test_the_anonymous_baseline_has_no_cookies_and_one_query(listed_asset):
    response, sql = anonymous_answer()

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert not response.cookies
    assert len(sql) == 1
    assert_never_authenticates(sql)


def test_a_valid_session_is_never_read_and_the_answer_is_the_same(member, listed_asset):
    baseline, _ = anonymous_answer()
    key = valid_session_key(member)

    response, sql = fetch_with_cookie(key)

    assert_same_as_anonymous(response, baseline)
    assert len(sql) == 1
    assert_never_authenticates(sql)


def test_an_expired_session_is_never_read_and_the_answer_is_the_same(
    member, listed_asset
):
    baseline, _ = anonymous_answer()
    key = expired_session_key(member)

    response, sql = fetch_with_cookie(key)

    assert_same_as_anonymous(response, baseline)
    assert len(sql) == 1
    assert_never_authenticates(sql)


@pytest.mark.parametrize("cookie", ["short", "!" * 40, UNKNOWN_KEY])
def test_a_malformed_or_unknown_cookie_changes_nothing(listed_asset, cookie):
    baseline, _ = anonymous_answer()

    response, sql = fetch_with_cookie(cookie)

    assert_same_as_anonymous(response, baseline)
    assert len(sql) == 1
    assert_never_authenticates(sql)


def test_the_session_cookie_is_not_refreshed_or_deleted(member, listed_asset):
    key = valid_session_key(member)
    before = Session.objects.get(session_key=key).expire_date

    response, _ = fetch_with_cookie(key)

    assert settings.SESSION_COOKIE_NAME not in response.cookies
    assert Session.objects.get(session_key=key).expire_date == before
