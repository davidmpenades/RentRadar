import pytest
from django.db import connection

from conftest import ensure_isolated_test_database


@pytest.mark.django_db
def test_suite_runs_on_the_dedicated_test_database():
    assert connection.settings_dict["NAME"] == "rentradar_test"


def test_guard_accepts_a_test_database_distinct_from_development():
    ensure_isolated_test_database("rentradar_test", "rentradar")


@pytest.mark.parametrize(
    ("test_name", "development_name"),
    [
        ("rentradar", "rentradar"),
        ("rentradar_dev", "rentradar"),
        ("rentradar_test", "rentradar_test"),
        ("", "rentradar"),
    ],
)
def test_guard_aborts_on_unsafe_names(test_name, development_name):
    with pytest.raises(pytest.UsageError):
        ensure_isolated_test_database(test_name, development_name)
