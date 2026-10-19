import pytest
from django.conf import settings as django_settings

from config.tests.conftest import DEVELOPMENT_ENVIRON
from config.tests.test_production import VALID_ENVIRON

FORBIDDEN_MARKERS = ("Traceback", "/app/", "SELECT", "RuntimeError", "missing-route")
PRODUCTION_ENVIRON = {k: v for k, v in VALID_ENVIRON.items() if k != "DJANGO_ENV"}


@pytest.fixture
def hardened(settings):
    settings.ROOT_URLCONF = "config.tests.urls"
    settings.ALLOWED_HOSTS = ["example.com"]
    return settings


@pytest.fixture
def client(hardened, client):
    client.raise_request_exception = False
    return client


def assert_generic(response, status):
    assert response.status_code == status
    body = response.content.decode()
    for marker in (*FORBIDDEN_MARKERS, django_settings.SECRET_KEY):
        assert marker not in body


def test_common_middleware_is_enabled():
    assert "django.middleware.common.CommonMiddleware" in django_settings.MIDDLEWARE


def test_disallowed_host_gets_generic_400(client):
    response = client.get("/only-get/", headers={"host": "evil.test"})

    assert_generic(response, 400)


def test_unknown_route_gets_generic_404(client):
    response = client.get("/missing-route/", headers={"host": "example.com"})

    assert_generic(response, 404)


def test_wrong_method_gets_generic_405(client):
    response = client.post("/only-get/", headers={"host": "example.com"})

    assert_generic(response, 405)


def test_unhandled_error_gets_generic_500(client):
    response = client.get("/explode/", headers={"host": "example.com"})

    assert_generic(response, 500)


def cookies_after_start(client):
    response = client.get("/start-session/", headers={"host": "example.com"})
    return response.cookies["sessionid"], response.cookies["csrftoken"]


@pytest.mark.django_db
def test_session_cookie_is_http_only_and_lax(client):
    session, _ = cookies_after_start(client)

    assert session["httponly"]
    assert session["samesite"] == "Lax"


@pytest.mark.django_db
def test_csrf_cookie_is_readable_by_scripts_and_lax(client):
    _, csrf = cookies_after_start(client)

    assert not csrf["httponly"]
    assert csrf["samesite"] == "Lax"


@pytest.mark.django_db
def test_cookies_are_not_secure_outside_production(client):
    session, csrf = cookies_after_start(client)

    assert not session["secure"]
    assert not csrf["secure"]


@pytest.mark.parametrize("env", ["development", "test", "production"])
def test_cookie_policy_in_every_environment(load_settings, env):
    environ = PRODUCTION_ENVIRON if env == "production" else DEVELOPMENT_ENVIRON
    module = load_settings(env, **environ)

    assert module.SESSION_COOKIE_HTTPONLY is True
    assert module.CSRF_COOKIE_HTTPONLY is False
    assert module.CSRF_USE_SESSIONS is False
    assert module.SESSION_COOKIE_SAMESITE == "Lax"
    assert module.CSRF_COOKIE_SAMESITE == "Lax"


@pytest.mark.django_db
def test_production_cookies_are_secure(load_settings, hardened, client):
    production = load_settings("production", **PRODUCTION_ENVIRON)
    hardened.SESSION_COOKIE_SECURE = production.SESSION_COOKIE_SECURE
    hardened.CSRF_COOKIE_SECURE = production.CSRF_COOKIE_SECURE

    session, csrf = cookies_after_start(client)

    assert session["secure"]
    assert csrf["secure"]
