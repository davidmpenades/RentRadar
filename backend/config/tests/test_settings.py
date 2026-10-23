import pytest
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone as django_timezone

from config.tests.conftest import DEVELOPMENT_ENVIRON, PRODUCTION_ENVIRON


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("1", True),
        ("TRUE", True),
        ("false", False),
        ("0", False),
        ("", False),
    ],
)
def test_development_debug_follows_variable(load_settings, raw, expected):
    settings = load_settings("development", DJANGO_DEBUG=raw, **DEVELOPMENT_ENVIRON)

    assert settings.DEBUG is expected


def test_development_debug_is_off_when_variable_is_missing(load_settings):
    settings = load_settings("development", **DEVELOPMENT_ENVIRON)

    assert settings.DEBUG is False


@pytest.mark.parametrize("raw", ["true", "1"])
def test_test_environment_keeps_debug_off(load_settings, raw):
    settings = load_settings("test", DJANGO_DEBUG=raw, **DEVELOPMENT_ENVIRON)

    assert settings.DEBUG is False


@pytest.mark.parametrize("env", ["development", "test"])
def test_non_boolean_debug_names_the_variable(load_settings, env):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_DEBUG"):
        load_settings(env, DJANGO_DEBUG="yes", **DEVELOPMENT_ENVIRON)


@pytest.mark.parametrize("env", ["development", "test", "production"])
def test_time_and_language_are_fixed(load_settings, env):
    environ = PRODUCTION_ENVIRON if env == "production" else DEVELOPMENT_ENVIRON
    settings = load_settings(env, **environ)

    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "UTC"
    assert settings.LANGUAGE_CODE == "es"
    assert settings.USE_I18N is True


def test_now_is_timezone_aware():
    assert django_timezone.now().tzinfo is not None


MD5_HASHER = "django.contrib.auth.hashers.MD5PasswordHasher"


def test_test_environment_uses_a_fast_password_hasher(load_settings):
    settings = load_settings("test", **DEVELOPMENT_ENVIRON)

    assert settings.PASSWORD_HASHERS == [MD5_HASHER]


@pytest.mark.parametrize("env", ["base", "production"])
def test_real_environments_keep_the_default_password_hashers(load_settings, env):
    environ = PRODUCTION_ENVIRON if env == "production" else {}
    settings = load_settings(env, **environ)

    assert not hasattr(settings, "PASSWORD_HASHERS")
