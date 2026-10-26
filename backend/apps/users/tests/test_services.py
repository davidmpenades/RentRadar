import traceback

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import identify_hasher
from django.db import DatabaseError, IntegrityError

from apps.core.errors import DomainValidationError
from apps.users import services
from apps.users.models import User
from apps.users.services import change_user_email, create_superuser, create_user

PASSWORD = "correct horse battery staple"
EMAIL_SUFFIX = "@correo.es"
PLAN_ERROR_CODES = {
    "email_empty",
    "email_invalid",
    "email_control_char",
    "email_too_long",
    "email_taken",
    "password_required",
    "password_invalid",
    "password_too_long",
    "constraint_violated",
    "validation_failed",
}
INVALID_EMAILS = [
    ("", {"email_empty"}),
    ("   ", {"email_empty"}),
    (None, {"email_empty"}),
    ("ana", {"email_invalid"}),
    ("ana@", {"email_invalid"}),
    ("a\x00na@x.es", {"email_invalid", "email_control_char"}),
    ("an\ta@x.es", {"email_invalid", "email_control_char"}),
    ("an\na@x.es", {"email_invalid", "email_control_char"}),
    ('"a\x01b"@x.es', {"email_control_char"}),
    (123, {"email_invalid"}),
]
# Si alguien separa los dos flujos de alta, los rechazos fallan en el que se desvíe
CREATE_FUNCTIONS = pytest.mark.parametrize(
    "create", [create_user, create_superuser], ids=["user", "superuser"]
)


def email_of_length(length):
    return "a" * (length - len(EMAIL_SUFFIX)) + EMAIL_SUFFIX


def codes_of(raised):
    return {field: set(codes) for field, codes in raised.value.message_dict.items()}


def skip_validation(monkeypatch):
    # Simula la carrera: otra alta entra entre la validación y el INSERT
    monkeypatch.setattr(User, "full_clean", lambda self, *args, **kwargs: None)


def trap_make_password(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("make_password no debe llamarse ante un rechazo")

    monkeypatch.setattr("django.contrib.auth.base_user.make_password", fail)


def stored_email(user):
    return User.objects.values_list("email", flat=True).get(pk=user.pk)


@pytest.mark.django_db
def test_user_authenticates_with_the_email_in_any_case():
    user = create_user(email="ana@correo.es", password=PASSWORD)

    assert authenticate(email="ANA@Correo.ES", password=PASSWORD) == user


@pytest.mark.django_db
def test_create_user_stores_the_normalized_email():
    user = create_user(email=" Ana@Correo.ES\n", password=PASSWORD)
    user.refresh_from_db()

    assert user.email == "ana@correo.es"


@pytest.mark.django_db
def test_create_user_stores_only_a_password_hash():
    user = create_user(email="ana@correo.es", password=PASSWORD)
    user.refresh_from_db()

    assert user.password != PASSWORD
    identify_hasher(user.password)
    assert user.check_password(PASSWORD)
    stored = User.objects.values().get(pk=user.pk)
    assert all(PASSWORD not in str(value) for value in stored.values())


@pytest.mark.django_db
@CREATE_FUNCTIONS
@pytest.mark.parametrize(("email", "expected"), INVALID_EMAILS)
def test_creation_rejects_invalid_emails(create, email, expected):
    with pytest.raises(DomainValidationError) as raised:
        create(email=email, password=PASSWORD)

    assert codes_of(raised) == {"email": expected}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_email_of_254_characters_is_accepted():
    user = create_user(email=email_of_length(254), password=PASSWORD)

    assert len(user.email) == 254


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_email_of_255_characters_is_too_long(create):
    with pytest.raises(DomainValidationError) as raised:
        create(email=email_of_length(255), password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_too_long"}}
    assert not User.objects.exists()


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_exact_duplicate_email_is_taken(create):
    create_user(email="ana@correo.es", password=PASSWORD)

    with pytest.raises(DomainValidationError) as raised:
        create(email="ANA@correo.es", password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert User.objects.count() == 1


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_email_differing_only_in_case_is_taken(create):
    # Fila guardada sin normalizar: solo la restricción con Lower la detecta
    User(email="Ana@Correo.ES").save()

    with pytest.raises(DomainValidationError) as raised:
        create(email="ana@correo.es", password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert User.objects.count() == 1


@pytest.mark.django_db
@CREATE_FUNCTIONS
@pytest.mark.parametrize("existing", ["Ana@Correo.ES", "ana@correo.es"])
def test_concurrent_duplicate_is_translated_to_email_taken(
    monkeypatch, create, existing
):
    User(email=existing).save()
    skip_validation(monkeypatch)

    with pytest.raises(DomainValidationError) as raised:
        create(email="ana@correo.es", password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    # La conexión sigue usable tras el rollback del atomic
    assert User.objects.count() == 1


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_integrity_error_without_details_is_not_swallowed(monkeypatch, create):
    def fail(self, *args, **kwargs):
        raise IntegrityError("sin diagnóstico")

    monkeypatch.setattr(User, "save", fail)

    with pytest.raises(DomainValidationError) as raised:
        create(email="ana@correo.es", password=PASSWORD)

    assert raised.value.message_dict == {"__all__": ["constraint_violated"]}


@pytest.mark.django_db
@CREATE_FUNCTIONS
@pytest.mark.parametrize("password", [None, ""])
def test_missing_password_is_required(create, password):
    with pytest.raises(DomainValidationError) as raised:
        create(email="ana@correo.es", password=password)

    assert codes_of(raised) == {"password": {"password_required"}}
    assert not User.objects.exists()


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_non_text_password_is_invalid(create):
    with pytest.raises(DomainValidationError) as raised:
        create(email="ana@correo.es", password=12345678)

    assert codes_of(raised) == {"password": {"password_invalid"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_password_of_128_characters_is_accepted():
    user = create_user(email="ana@correo.es", password="p" * 128)

    assert user.check_password("p" * 128)


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_password_of_129_characters_is_too_long(create):
    with pytest.raises(DomainValidationError) as raised:
        create(email="ana@correo.es", password="p" * 129)

    assert codes_of(raised) == {"password": {"password_too_long"}}
    assert not User.objects.exists()


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_password_and_email_errors_are_reported_together(create):
    with pytest.raises(DomainValidationError) as raised:
        create(email="ana", password=None)

    assert codes_of(raised) == {
        "email": {"email_invalid"},
        "password": {"password_required"},
    }


@pytest.mark.django_db
@CREATE_FUNCTIONS
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("ana", PASSWORD),
        ("ana@correo.es", None),
        ("ana@correo.es", "p" * 129),
        ("taken@correo.es", PASSWORD),
    ],
)
def test_rejections_never_compute_the_hash(monkeypatch, create, email, password):
    User(email="taken@correo.es").save()
    trap_make_password(monkeypatch)

    with pytest.raises(DomainValidationError):
        create(email=email, password=password)


@pytest.mark.django_db
@CREATE_FUNCTIONS
def test_hash_guard_fires_on_a_valid_creation(monkeypatch, create):
    trap_make_password(monkeypatch)

    with pytest.raises(AssertionError, match="make_password"):
        create(email="ana@correo.es", password=PASSWORD)


@pytest.mark.django_db
def test_ordinary_user_gets_no_admin_permissions():
    user = create_user(email="ana@correo.es", password=PASSWORD)
    user.refresh_from_db()

    assert user.is_staff is False
    assert user.is_superuser is False
    assert not user.groups.exists()
    assert not user.user_permissions.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "create",
    [
        create_user,
        create_superuser,
        User.objects.create_user,
        User.objects.create_superuser,
    ],
)
def test_admin_flags_cannot_be_passed(create):
    with pytest.raises(TypeError):
        create(email="ana@correo.es", password=PASSWORD, is_staff=True)

    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "create",
    [
        create_user,
        create_superuser,
        User.objects.create_user,
        User.objects.create_superuser,
    ],
)
def test_arguments_must_be_passed_by_name(create):
    with pytest.raises(TypeError):
        create("ana@correo.es", PASSWORD)

    assert not User.objects.exists()


@pytest.mark.django_db
def test_manager_create_user_delegates_to_the_service():
    user = User.objects.create_user(email=" Ana@Correo.ES ", password=PASSWORD)
    user.refresh_from_db()

    assert user.email == "ana@correo.es"
    assert user.check_password(PASSWORD)


@pytest.mark.django_db
def test_change_user_email_stores_the_normalized_email():
    user = create_user(email="ana@correo.es", password=PASSWORD)

    returned = change_user_email(user=user, email=" NUEVA@Correo.ES ")

    assert returned is user
    assert user.email == "nueva@correo.es"
    assert stored_email(user) == "nueva@correo.es"


@pytest.mark.django_db
@pytest.mark.parametrize(("email", "expected"), INVALID_EMAILS)
def test_change_user_email_rejects_invalid_emails_without_changes(email, expected):
    user = create_user(email="ana@correo.es", password=PASSWORD)

    with pytest.raises(DomainValidationError) as raised:
        change_user_email(user=user, email=email)

    assert codes_of(raised) == {"email": expected}
    assert user.email == "ana@correo.es"
    assert stored_email(user) == "ana@correo.es"


@pytest.mark.django_db
@pytest.mark.parametrize("other", ["ana@correo.es", "Ana@Correo.ES"])
def test_change_user_email_to_another_users_email_is_taken(other):
    # La segunda fila se guarda sin normalizar: solo la restricción con Lower la detecta
    User(email=other).save()
    user = create_user(email="luis@correo.es", password=PASSWORD)

    with pytest.raises(DomainValidationError) as raised:
        change_user_email(user=user, email="ANA@correo.es")

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert user.email == "luis@correo.es"
    assert stored_email(user) == "luis@correo.es"


@pytest.mark.django_db
@pytest.mark.parametrize("current", ["ana@correo.es", "Ana@Correo.ES"])
def test_change_user_email_to_its_own_email_in_other_case_is_accepted(current):
    user = User(email=current)
    user.save()

    change_user_email(user=user, email="ANA@correo.es")

    assert stored_email(user) == "ana@correo.es"


@pytest.mark.django_db
def test_concurrent_email_change_restores_the_instance(monkeypatch):
    User(email="ana@correo.es").save()
    user = create_user(email="luis@correo.es", password=PASSWORD)
    skip_validation(monkeypatch)

    with pytest.raises(DomainValidationError) as raised:
        change_user_email(user=user, email="ana@correo.es")

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert user.email == "luis@correo.es"
    assert stored_email(user) == "luis@correo.es"


@pytest.mark.django_db
def test_change_user_email_does_not_overwrite_other_columns():
    user = create_user(email="ana@correo.es", password=PASSWORD)
    # Otro proceso cambia la fila después de que se cargara la instancia
    User.objects.filter(pk=user.pk).update(first_name="Ana")

    change_user_email(user=user, email="nueva@correo.es")

    assert User.objects.get(pk=user.pk).first_name == "Ana"


@pytest.mark.django_db
def test_change_user_email_of_a_deleted_user_fails_without_the_email():
    user = create_user(email="ana@correo.es", password=PASSWORD)
    User.objects.filter(pk=user.pk).delete()

    with pytest.raises(DatabaseError) as raised:
        change_user_email(user=user, email="nueva@correo.es")

    # Solo la excepción: el traceback completo incluye el código fuente de la llamada
    rendered = "".join(traceback.format_exception_only(raised.value))
    assert str(raised.value) == "Save with update_fields did not affect any rows."
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert "nueva@correo.es" not in rendered
    assert "ana@correo.es" not in rendered


def test_error_codes_match_the_plan_table():
    assert services.ERROR_CODES == PLAN_ERROR_CODES
