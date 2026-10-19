from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError

from apps.core.management.commands import wait_for_db

HOST_SENTINEL = "sentinel-host.internal"
USER_SENTINEL = "sentinel_user"


@pytest.fixture
def fake_time(monkeypatch):
    state = {"now": 0.0}

    def sleep(seconds):
        state["now"] += seconds

    monkeypatch.setattr(wait_for_db, "monotonic", lambda: state["now"])
    monkeypatch.setattr(wait_for_db, "sleep", sleep)
    return state


def use_connection(monkeypatch, ensure_connection):
    stub = SimpleNamespace(ensure_connection=ensure_connection)
    monkeypatch.setattr(wait_for_db, "connection", stub)


def test_succeeds_when_the_database_is_available(monkeypatch, fake_time):
    use_connection(monkeypatch, lambda: None)

    call_command("wait_for_db")


def test_failure_message_is_fixed_and_leaks_nothing(monkeypatch, fake_time, capsys):
    def ensure_connection():
        raise OperationalError(
            f'connection to server at "{HOST_SENTINEL}", user "{USER_SENTINEL}" failed'
        )

    use_connection(monkeypatch, ensure_connection)

    with pytest.raises(CommandError) as error:
        call_command("wait_for_db")

    assert "base de datos" in str(error.value)
    captured = capsys.readouterr()
    visible = str(error.value) + captured.out + captured.err
    assert HOST_SENTINEL not in visible
    assert USER_SENTINEL not in visible
    assert error.value.__cause__ is None
    assert error.value.__context__ is None
    assert fake_time["now"] == 60.0
