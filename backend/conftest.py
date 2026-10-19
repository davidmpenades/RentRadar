import pytest
from django.conf import settings

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
