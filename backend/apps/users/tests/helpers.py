from apps.users.models import User


def skip_validation(monkeypatch):
    # Simula la carrera: otra alta entra entre la validación y el INSERT
    monkeypatch.setattr(User, "full_clean", lambda self, *args, **kwargs: None)
