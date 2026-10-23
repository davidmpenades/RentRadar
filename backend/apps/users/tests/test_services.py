import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import identify_hasher
from django.db import IntegrityError

from apps.core.errors import DomainValidationError
from apps.users import services
from apps.users.models import User
from apps.users.services import create_user

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


def email_of_length(length):
    return "a" * (length - len(EMAIL_SUFFIX)) + EMAIL_SUFFIX


def codes_of(raised):
    return {field: set(codes) for field, codes in raised.value.message_dict.items()}


def skip_validation(monkeypatch):
    # Simula la carrera: otra alta entra entre la validación y el INSERT
    monkeypatch.setattr(User, "full_clean", lambda self, *args, **kwargs: None)


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
@pytest.mark.parametrize(
    ("email", "expected"),
    [
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
    ],
)
def test_create_user_rejects_invalid_emails(email, expected):
    with pytest.raises(DomainValidationError) as raised:
        create_user(email=email, password=PASSWORD)

    assert codes_of(raised) == {"email": expected}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_email_of_254_characters_is_accepted():
    user = create_user(email=email_of_length(254), password=PASSWORD)

    assert len(user.email) == 254


@pytest.mark.django_db
def test_email_of_255_characters_is_too_long():
    with pytest.raises(DomainValidationError) as raised:
        create_user(email=email_of_length(255), password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_too_long"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_exact_duplicate_email_is_taken():
    create_user(email="ana@correo.es", password=PASSWORD)

    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ANA@correo.es", password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_email_differing_only_in_case_is_taken():
    # Fila guardada sin normalizar: solo la restricción con Lower la detecta
    User(email="Ana@Correo.ES").save()

    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ana@correo.es", password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert User.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("existing", ["Ana@Correo.ES", "ana@correo.es"])
def test_concurrent_duplicate_is_translated_to_email_taken(monkeypatch, existing):
    User(email=existing).save()
    skip_validation(monkeypatch)

    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ana@correo.es", password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    # La conexión sigue usable tras el rollback del atomic
    assert User.objects.count() == 1


def test_unknown_constraint_is_reported_without_details():
    assert services._codes_for_constraint("other_constraint") == {
        "__all__": ["constraint_violated"]
    }


@pytest.mark.django_db
def test_integrity_error_without_details_is_not_swallowed(monkeypatch):
    def fail(self, *args, **kwargs):
        raise IntegrityError("sin diagnóstico")

    monkeypatch.setattr(User, "save", fail)

    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ana@correo.es", password=PASSWORD)

    assert raised.value.message_dict == {"__all__": ["constraint_violated"]}


@pytest.mark.django_db
@pytest.mark.parametrize("password", [None, ""])
def test_missing_password_is_required(password):
    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ana@correo.es", password=password)

    assert codes_of(raised) == {"password": {"password_required"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_non_text_password_is_invalid():
    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ana@correo.es", password=12345678)

    assert codes_of(raised) == {"password": {"password_invalid"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_password_of_128_characters_is_accepted():
    user = create_user(email="ana@correo.es", password="p" * 128)

    assert user.check_password("p" * 128)


@pytest.mark.django_db
def test_password_of_129_characters_is_too_long():
    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ana@correo.es", password="p" * 129)

    assert codes_of(raised) == {"password": {"password_too_long"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_password_and_email_errors_are_reported_together():
    with pytest.raises(DomainValidationError) as raised:
        create_user(email="ana", password=None)

    assert codes_of(raised) == {
        "email": {"email_invalid"},
        "password": {"password_required"},
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("ana", PASSWORD),
        ("ana@correo.es", None),
        ("ana@correo.es", "p" * 129),
        ("taken@correo.es", PASSWORD),
    ],
)
def test_rejections_never_compute_the_hash(monkeypatch, email, password):
    User(email="taken@correo.es").save()

    def fail(*args, **kwargs):
        raise AssertionError("make_password no debe llamarse ante un rechazo")

    monkeypatch.setattr("django.contrib.auth.base_user.make_password", fail)

    with pytest.raises(DomainValidationError):
        create_user(email=email, password=password)


@pytest.mark.django_db
def test_hash_guard_fires_on_a_valid_creation(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("make_password no debe llamarse ante un rechazo")

    monkeypatch.setattr("django.contrib.auth.base_user.make_password", fail)

    with pytest.raises(AssertionError, match="make_password"):
        create_user(email="ana@correo.es", password=PASSWORD)


@pytest.mark.django_db
def test_ordinary_user_gets_no_admin_permissions():
    user = create_user(email="ana@correo.es", password=PASSWORD)
    user.refresh_from_db()

    assert user.is_staff is False
    assert user.is_superuser is False
    assert not user.groups.exists()
    assert not user.user_permissions.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("create", [create_user, User.objects.create_user])
def test_admin_flags_cannot_be_passed(create):
    with pytest.raises(TypeError):
        create(email="ana@correo.es", password=PASSWORD, is_staff=True)

    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("create", [create_user, User.objects.create_user])
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


def test_error_codes_match_the_plan_table():
    assert services.ERROR_CODES == PLAN_ERROR_CODES
