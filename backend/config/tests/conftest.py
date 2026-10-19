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
