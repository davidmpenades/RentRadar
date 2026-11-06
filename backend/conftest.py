import socket

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client

from config.env import read_optional


def ensure_isolated_test_database(test_name: str, development_name: str) -> None:
    if "test" not in test_name or test_name == development_name:
        raise pytest.UsageError(
            "La base de datos de test debe contener «test» y ser distinta de DB_NAME."
        )


def pytest_sessionstart(session):
    database = settings.DATABASES["default"]
    development_name = read_optional(None, "DB_NAME")
    # Django crea y borra TEST["NAME"], y NAME es la que se abriría si se omitiera
    for name in (database["NAME"], database["TEST"]["NAME"]):
        ensure_isolated_test_database(name, development_name)


@pytest.fixture(autouse=True)
def clear_default_cache():
    # Los contadores del límite viven en la caché: no pasan de un test a otro
    cache.clear()


class NetworkBlockedError(RuntimeError):
    pass


def _blocked(*args, **kwargs):
    raise NetworkBlockedError("Red bloqueada en los tests")


@pytest.fixture(autouse=True)
def block_internet_sockets(monkeypatch):
    # Solo bloquea sockets de Python; libpq (BD de test) y AF_UNIX siguen funcionando
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _blocked()
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)


@pytest.fixture
def csrf_client():
    # El cliente por defecto se salta la comprobación CSRF: este la exige
    return Client(enforce_csrf_checks=True)
