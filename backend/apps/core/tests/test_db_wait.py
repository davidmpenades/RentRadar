import pytest
from django.db import OperationalError

from apps.core.db_wait import wait_until_available


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_returns_true_when_the_database_becomes_available_late():
    clock = FakeClock()
    attempts = []

    def check():
        attempts.append(clock.now)
        if len(attempts) <= 2:
            raise OperationalError("not ready")

    assert wait_until_available(check, clock, clock.sleep) is True
    assert len(attempts) == 3
    assert clock.sleeps == [1.0, 1.0]


def test_returns_true_without_sleeping_when_already_available():
    clock = FakeClock()

    assert wait_until_available(lambda: None, clock, clock.sleep) is True
    assert clock.sleeps == []


def test_returns_false_when_the_deadline_expires():
    clock = FakeClock()

    def check():
        raise OperationalError("never ready")

    assert wait_until_available(check, clock, clock.sleep, timeout=60.0) is False
    assert clock.now == 60.0


def test_only_operational_errors_are_retried():
    clock = FakeClock()

    def check():
        raise RuntimeError("unexpected")

    with pytest.raises(RuntimeError):
        wait_until_available(check, clock, clock.sleep)
    assert clock.sleeps == []
