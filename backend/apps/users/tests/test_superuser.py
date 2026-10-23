from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.users.models import User
from apps.users.services import create_superuser

PASSWORD = "correct horse battery staple"


@pytest.mark.django_db
def test_superuser_gets_admin_permissions():
    user = create_superuser(email="admin@correo.es", password=PASSWORD)
    user.refresh_from_db()

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True


@pytest.mark.django_db
def test_superuser_has_every_permission():
    user = create_superuser(email="admin@correo.es", password=PASSWORD)

    assert user.has_perm("any_app.any_permission")


@pytest.mark.django_db
def test_createsuperuser_without_password_variable_creates_nothing(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)

    with pytest.raises(CommandError, match="password_required"):
        call_command(
            "createsuperuser",
            interactive=False,
            email="admin@correo.es",
            stdout=StringIO(),
        )

    assert not User.objects.exists()


@pytest.mark.django_db
def test_createsuperuser_with_password_variable_creates_a_superuser(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", PASSWORD)

    call_command(
        "createsuperuser",
        interactive=False,
        email="Admin@Correo.ES",
        stdout=StringIO(),
    )

    user = User.objects.get()
    assert user.email == "admin@correo.es"
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password(PASSWORD)
