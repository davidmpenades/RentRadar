import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.tests.conftest import PASSWORD_SENTINEL, SECRET_SENTINEL, VALID_ENVIRON

REQUIRED = [name for name in VALID_ENVIRON if name != "DJANGO_ENV"]
SENTINELS = (SECRET_SENTINEL, PASSWORD_SENTINEL, "sentinel-db-host", "sentinel_user")


def run_check(**overrides):
    # Entorno limpio: solo PATH y las variables de producción; None elimina una variable
    environ = {"PATH": os.environ["PATH"], **VALID_ENVIRON, **overrides}
    environ = {name: value for name, value in environ.items() if value is not None}
    return subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=settings.BASE_DIR,
        env=environ,
        capture_output=True,
        text=True,
        timeout=60,
    )


def assert_refused(result, variable):
    assert result.returncode != 0
    assert variable in result.stderr
    for sentinel in SENTINELS:
        assert sentinel not in result.stdout + result.stderr


def test_valid_production_config_passes_check():
    result = run_check()

    assert result.returncode == 0, result.stderr


def test_every_required_variable_is_named_when_all_are_empty():
    result = run_check(**dict.fromkeys(REQUIRED, ""))

    assert_refused(result, REQUIRED[0])
    for variable in REQUIRED[1:]:
        assert variable in result.stderr


@pytest.mark.parametrize("port", ["abc", "0", "70000"])
def test_invalid_port_is_refused(port):
    result = run_check(DB_PORT=port)

    assert_refused(result, "DB_PORT")


def test_short_secret_key_is_refused():
    result = run_check(DJANGO_SECRET_KEY="s" * 49)

    assert_refused(result, "DJANGO_SECRET_KEY")


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("DJANGO_SECRET_KEY", "insecure-" + "s" * 50),
        ("DB_PASSWORD", "insecure-dev-db-password"),
    ],
)
def test_insecure_marker_is_refused(variable, value):
    result = run_check(**{variable: value})

    assert_refused(result, variable)
    assert value not in result.stderr


@pytest.mark.parametrize("hosts", ["*", "rentradar.example,*", "http://example.com"])
def test_invalid_allowed_hosts_are_refused(hosts):
    result = run_check(DJANGO_ALLOWED_HOSTS=hosts)

    assert_refused(result, "DJANGO_ALLOWED_HOSTS")


@pytest.mark.parametrize("raw", ["yes", "on"])
def test_non_boolean_debug_is_refused(raw):
    result = run_check(DJANGO_DEBUG=raw)

    assert_refused(result, "DJANGO_DEBUG")


def test_debug_stays_off_in_production(load_settings):
    module = load_settings("production", **{**VALID_ENVIRON, "DJANGO_DEBUG": "true"})

    assert module.DEBUG is False


def test_production_settings_come_from_the_validated_config(load_settings):
    module = load_settings("production", **VALID_ENVIRON)

    assert module.SECRET_KEY == SECRET_SENTINEL
    assert module.ALLOWED_HOSTS == ["rentradar.example", ".example.com"]
    assert module.DATABASES["default"]["PORT"] == 5432


def test_invalid_production_config_raises_when_imported(load_settings):
    with pytest.raises(ImproperlyConfigured):
        load_settings("production", **{**VALID_ENVIRON, "DB_PORT": "0"})
