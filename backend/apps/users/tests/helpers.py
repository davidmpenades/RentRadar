from contextlib import ExitStack, contextmanager
from unittest import mock

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session

from apps.users.models import User


def skip_validation(monkeypatch):
    # Simula la carrera: otra alta entra entre la validación y el INSERT
    monkeypatch.setattr(User, "full_clean", lambda self, *args, **kwargs: None)


def assert_no_store(response):
    assert response["Cache-Control"] == "no-store"


def assert_throttled(response):
    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "throttled"
    assert isinstance(body["retry_after"], int)
    assert body["retry_after"] >= 1
    assert response["Retry-After"] == str(body["retry_after"])
    return body["retry_after"]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def stored_sessions():
    return list(
        Session.objects.order_by("session_key").values_list(
            "session_key", "session_data", "expire_date"
        )
    )


@contextmanager
def untouchable_session_store():
    # Cualquier lectura o escritura de la sesión hace fallar la petición
    names = ("load", "save", "create", "delete", "flush", "cycle_key", "clear")
    with ExitStack() as stack:
        for name in names:
            stack.enter_context(
                mock.patch.object(
                    SessionStore, name, side_effect=AssertionError(f"session.{name}")
                )
            )
        yield


def cross_origin_headers(response):
    return [n for n in response.headers if n.lower().startswith("access-control-")]
