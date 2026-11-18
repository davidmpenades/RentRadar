from apps.users.models import User


def skip_validation(monkeypatch):
    # Simula la carrera: otra alta entra entre la validación y el INSERT
    monkeypatch.setattr(User, "full_clean", lambda self, *args, **kwargs: None)


def assert_no_store(response):
    assert response["Cache-Control"] == "no-store"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds
