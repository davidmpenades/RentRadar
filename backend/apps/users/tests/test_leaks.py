import logging
import traceback
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import connection

from apps.core.errors import DomainValidationError
from apps.users.models import User
from apps.users.services import change_user_email, create_superuser, create_user

# La marca no aparece en ningún identificador: el traceback imprime el código fuente
MARK = "zq7x"
EMAIL = f"{MARK}.ana@correo.es"
EMAIL_OTHER_CASE = f"{MARK.upper()}.Ana@Correo.ES"
PASSWORD = f"{MARK} correct horse battery staple"
LONG_EMAIL = MARK + "a" * (255 - len(MARK) - len("@correo.es")) + "@correo.es"
LONG_PASSWORD = MARK + "p" * (129 - len(MARK))
OWN_EMAIL = "luis@correo.es"

CREATE_FUNCTIONS = pytest.mark.parametrize(
    "create", [create_user, create_superuser], ids=["user", "superuser"]
)
# (email ya guardado, email recibido, contraseña, carrera sin validación)
CREATION_CASES = {
    "duplicate_in_validation": (EMAIL, EMAIL_OTHER_CASE, PASSWORD, False),
    "duplicate_in_database": (EMAIL, EMAIL_OTHER_CASE, PASSWORD, True),
    "exact_duplicate_in_database": (EMAIL, EMAIL, PASSWORD, True),
    "email_too_long": (None, LONG_EMAIL, PASSWORD, False),
    "control_character": (None, f"{MARK}\x00@correo.es", PASSWORD, False),
    "invalid_format": (None, f"{MARK}.ana", PASSWORD, False),
    "password_too_long": (None, EMAIL, LONG_PASSWORD, False),
    "missing_password": (None, EMAIL, None, False),
}
CHANGE_CASES = {
    "duplicate_in_validation": (EMAIL, EMAIL_OTHER_CASE, False),
    "duplicate_in_database": (EMAIL, EMAIL_OTHER_CASE, True),
    "control_character": (None, f"{MARK}\x00@correo.es", False),
    "invalid_format": (None, f"{MARK}.ana", False),
}


def skip_validation(monkeypatch):
    # Simula la carrera: otra alta entra entre la validación y el INSERT
    monkeypatch.setattr(User, "full_clean", lambda self, *args, **kwargs: None)


def log_every_sql(monkeypatch, caplog):
    # El cursor de depuración hace que Django intente registrar cada SQL con sus valores
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(connection, "force_debug_cursor", True)
    caplog.clear()


def assert_no_leak(error, caplog):
    texts = [
        str(error),
        repr(error),
        "".join(traceback.format_exception(error)),
        caplog.text,
    ]
    if isinstance(error, DomainValidationError):
        texts.append(str(error.message_dict))
        assert error.__context__ is None
        assert error.__cause__ is None
    for text in texts:
        assert MARK not in text.lower()


@pytest.mark.django_db
@CREATE_FUNCTIONS
@pytest.mark.parametrize(
    ("existing", "email", "password", "race"),
    list(CREATION_CASES.values()),
    ids=list(CREATION_CASES),
)
def test_creation_rejections_do_not_leak(
    monkeypatch, caplog, create, existing, email, password, race
):
    if existing:
        User(email=existing).save()
    if race:
        skip_validation(monkeypatch)
    log_every_sql(monkeypatch, caplog)

    with pytest.raises(DomainValidationError) as raised:
        create(email=email, password=password)

    assert_no_leak(raised.value, caplog)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("existing", "email", "race"),
    list(CHANGE_CASES.values()),
    ids=list(CHANGE_CASES),
)
def test_email_change_rejections_do_not_leak(
    monkeypatch, caplog, existing, email, race
):
    user = create_user(email=OWN_EMAIL, password=PASSWORD)
    if existing:
        User(email=existing).save()
    if race:
        skip_validation(monkeypatch)
    log_every_sql(monkeypatch, caplog)

    with pytest.raises(DomainValidationError) as raised:
        change_user_email(user=user, email=email)

    assert_no_leak(raised.value, caplog)


@pytest.mark.django_db
def test_createsuperuser_without_password_does_not_leak(monkeypatch, caplog):
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
    log_every_sql(monkeypatch, caplog)
    stderr = StringIO()

    with pytest.raises(CommandError) as raised:
        call_command(
            "createsuperuser",
            interactive=False,
            email=EMAIL,
            stdout=StringIO(),
            stderr=stderr,
        )

    assert_no_leak(raised.value, caplog)
    assert MARK not in stderr.getvalue().lower()


@pytest.mark.django_db
def test_user_text_does_not_contain_the_email():
    user = create_user(email=EMAIL, password=PASSWORD)

    assert MARK not in str(user).lower()
    assert MARK not in repr(user).lower()
