import importlib
import sys

import pytest

from config.env import KNOWN_VARIABLES

DEVELOPMENT_ENVIRON = {
    "DJANGO_SECRET_KEY": "insecure-dev-only-not-a-secret",
    "DB_HOST": "db",
    "DB_PORT": "5432",
    "DB_NAME": "rentradar",
    "DB_USER": "rentradar",
    "DB_PASSWORD": "insecure-dev-only-not-a-secret",
}
SECRET_SENTINEL = "sentinel-secret-key-" + "k" * 40
PASSWORD_SENTINEL = "sentinel-db-password-xyz"
VALID_ENVIRON = {
    "DJANGO_ENV": "production",
    "DJANGO_SECRET_KEY": SECRET_SENTINEL,
    "DJANGO_ALLOWED_HOSTS": "rentradar.example,.example.com",
    "DB_HOST": "sentinel-db-host",
    "DB_PORT": "5432",
    "DB_NAME": "sentinel_db",
    "DB_USER": "sentinel_user",
    "DB_PASSWORD": PASSWORD_SENTINEL,
}
PRODUCTION_ENVIRON = {k: v for k, v in VALID_ENVIRON.items() if k != "DJANGO_ENV"}


def _forget_settings_modules():
    for name in list(sys.modules):
        if name.startswith("config.settings"):
            del sys.modules[name]


@pytest.fixture
def load_settings(monkeypatch):
    def load(env, **environ):
        for name in KNOWN_VARIABLES:
            monkeypatch.delenv(name, raising=False)
        for name, value in environ.items():
            monkeypatch.setenv(name, value)
        _forget_settings_modules()
        return importlib.import_module(f"config.settings.{env}")

    yield load
    _forget_settings_modules()
