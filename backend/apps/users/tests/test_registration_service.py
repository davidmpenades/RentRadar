import pytest
from django.contrib.auth.hashers import identify_hasher
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.core.errors import DomainValidationError
from apps.users.models import User
from apps.users.services import register_user
from apps.users.tests.helpers import skip_validation

EMAIL = "ana@correo.es"
PASSWORD = "correct horse battery staple"
SURROGATE = chr(0xD800)
LOW_SURROGATE = chr(0xDFFF)
SURROGATE_EMAIL = "ana@" + SURROGATE + ".es"
WEAK_PASSWORD = "xk3vq"
ALL_DIGITS = "1234567890" * 12 + "123456789"


def password_of_length(length):
    return ("xk3vq9m2pw-" * 12)[:length]


def codes_of(raised):
    return {field: set(codes) for field, codes in raised.value.message_dict.items()}


def password_codes(raised):
    return raised.value.message_dict["password"]


def trap_make_password(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("make_password no debe llamarse ante un rechazo")

    monkeypatch.setattr("django.contrib.auth.base_user.make_password", fail)


def written_statements(queries):
    return [
        query["sql"]
        for query in queries
        if not query["sql"].lstrip().upper().startswith("SELECT")
    ]


@pytest.mark.django_db
def test_registration_stores_the_normalized_email():
    user = register_user(email=" Ana@Correo.ES\n", password=PASSWORD)
    user.refresh_from_db()

    assert user.email == "ana@correo.es"


@pytest.mark.django_db
def test_registration_stores_only_a_password_hash():
    user = register_user(email=EMAIL, password=PASSWORD)
    user.refresh_from_db()

    assert user.password != PASSWORD
    identify_hasher(user.password)
    assert user.check_password(PASSWORD)
    stored = User.objects.values().get(pk=user.pk)
    assert all(PASSWORD not in str(value) for value in stored.values())


@pytest.mark.django_db
def test_registered_user_gets_no_admin_permissions():
    user = register_user(email=EMAIL, password=PASSWORD)
    user.refresh_from_db()

    assert user.is_staff is False
    assert user.is_superuser is False
    assert not user.groups.exists()
    assert not user.user_permissions.exists()


@pytest.mark.django_db
def test_arguments_must_be_passed_by_name():
    with pytest.raises(TypeError):
        register_user(EMAIL, PASSWORD)

    assert not User.objects.exists()


@pytest.mark.django_db
def test_admin_flags_cannot_be_passed():
    with pytest.raises(TypeError):
        register_user(email=EMAIL, password=PASSWORD, is_staff=True)

    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("length", [10, 128])
def test_password_lengths_at_the_limits_are_accepted(length):
    password = password_of_length(length)

    user = register_user(email=EMAIL, password=password)

    assert len(password) == length
    assert user.check_password(password)


@pytest.mark.django_db
def test_password_of_9_characters_is_too_short():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=EMAIL, password=password_of_length(9))

    assert codes_of(raised) == {"password": {"password_too_short"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_password_of_129_characters_is_too_long_and_still_validated():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=EMAIL, password=ALL_DIGITS)

    assert len(ALL_DIGITS) == 129
    assert password_codes(raised) == ["password_too_long", "password_entirely_numeric"]
    assert not User.objects.exists()


@pytest.mark.django_db
def test_password_of_129_characters_is_rejected_without_hashing(monkeypatch):
    trap_make_password(monkeypatch)

    with pytest.raises(DomainValidationError) as raised:
        register_user(email=EMAIL, password=password_of_length(129))

    assert codes_of(raised) == {"password": {"password_too_long"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_hash_guard_fires_on_a_valid_registration(monkeypatch):
    trap_make_password(monkeypatch)

    with pytest.raises(AssertionError, match="make_password"):
        register_user(email=EMAIL, password=PASSWORD)


@pytest.mark.django_db
def test_every_password_rule_reports_in_the_documented_order():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email="1234567@correo.es", password="1234567")

    assert password_codes(raised) == [
        "password_too_short",
        "password_too_common",
        "password_entirely_numeric",
        "password_too_similar",
    ]
    assert not User.objects.exists()


@pytest.mark.django_db
def test_all_digit_common_password_gets_both_codes():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=EMAIL, password="1234567890")

    assert password_codes(raised) == [
        "password_too_common",
        "password_entirely_numeric",
    ]
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("password", ["QWERTYUIOP", "  qwertyuiop  "])
def test_common_password_is_rejected_ignoring_case_and_edge_spaces(password):
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=EMAIL, password=password)

    assert password_codes(raised) == ["password_too_common"]
    assert not User.objects.exists()


@pytest.mark.django_db
def test_password_equal_to_the_email_is_too_similar():
    email = "ana.lopez.garcia@correo.es"

    with pytest.raises(DomainValidationError) as raised:
        register_user(email=email, password=email)

    assert codes_of(raised) == {"password": {"password_too_similar"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_password_similar_to_the_normalized_email_is_too_similar():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=" Ana.Lopez.Garcia@Correo.ES ", password="ana.lopez.garcia")

    assert codes_of(raised) == {"password": {"password_too_similar"}}


@pytest.mark.django_db
def test_edge_spaces_are_kept_and_counted():
    password = "  xk3vq9  "

    user = register_user(email=EMAIL, password=password)
    user.refresh_from_db()

    # Recortada tendría 6 caracteres y no pasaría
    assert len(password) == 10
    assert user.check_password(password)
    assert not user.check_password(password.strip())


@pytest.mark.django_db
def test_email_errors_come_before_password_errors():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email="ana", password=WEAK_PASSWORD)

    assert list(raised.value.message_dict) == ["email", "password"]
    assert codes_of(raised) == {
        "email": {"email_invalid"},
        "password": {"password_too_short"},
    }


@pytest.mark.django_db
def test_taken_email_is_reported_together_with_password_errors():
    User(email=EMAIL).save()

    with pytest.raises(DomainValidationError) as raised:
        register_user(email="Ana@Correo.ES", password=WEAK_PASSWORD)

    assert list(raised.value.message_dict) == ["email", "password"]
    assert codes_of(raised) == {
        "email": {"email_taken"},
        "password": {"password_too_short"},
    }
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_missing_email_and_password_are_reported_as_empty_and_required():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=None, password=None)

    assert list(raised.value.message_dict) == ["email", "password"]
    assert codes_of(raised) == {
        "email": {"email_empty"},
        "password": {"password_required"},
    }


@pytest.mark.django_db
@pytest.mark.parametrize("password", [None, ""])
def test_missing_password_is_required_and_runs_no_validator(password):
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=EMAIL, password=password)

    assert codes_of(raised) == {"password": {"password_required"}}
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "password", [12345678901, ["xk3vq9m2pw"], {"a": "b"}, b"x" * 12]
)
def test_non_text_password_is_invalid(password):
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=EMAIL, password=password)

    assert codes_of(raised) == {"password": {"password_invalid"}}
    assert not User.objects.exists()


@pytest.mark.django_db
def test_non_text_email_is_invalid():
    with pytest.raises(DomainValidationError) as raised:
        register_user(email=123, password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_invalid"}}
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "password",
    [
        "p" * 5 + "\x00" + "p" * 5,
        "\x00",
        SURROGATE * 12,
        LOW_SURROGATE,
        "p" * 5 + SURROGATE + "p" * 5,
        "p" * 130 + SURROGATE,
    ],
    ids=["nul", "only-nul", "surrogate", "low-surrogate", "in-the-middle", "too-long"],
)
def test_nul_or_surrogate_in_the_password_is_invalid_and_alone(monkeypatch, password):
    trap_make_password(monkeypatch)

    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(DomainValidationError) as raised,
    ):
        register_user(email=EMAIL, password=password)

    # El email es válido: lo único que sale a la BD es la comprobación de unicidad
    assert codes_of(raised) == {"password": {"password_invalid"}}
    assert password_codes(raised) == ["password_invalid"]
    assert written_statements(queries) == []
    assert not User.objects.exists()


@pytest.mark.django_db
def test_nul_in_the_email_is_rejected_without_a_query_on_users():
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(DomainValidationError) as raised,
    ):
        register_user(email="a\x00na@correo.es", password=PASSWORD)

    # El campo con errores queda fuera de la comprobación de unicidad
    assert codes_of(raised) == {"email": {"email_invalid", "email_control_char"}}
    assert [q["sql"] for q in queries if "users_user" in q["sql"]] == []
    assert not User.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "email",
    [
        SURROGATE_EMAIL,
        SURROGATE + "@correo.es",
        "ana@correo." + LOW_SURROGATE,
        " Ana@" + SURROGATE + ".ES ",
    ],
    ids=["domain", "local-part", "low-surrogate", "needs-normalizing"],
)
def test_surrogate_in_the_email_is_invalid_with_no_query(email):
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(DomainValidationError) as raised,
    ):
        register_user(email=email, password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_invalid"}}
    assert len(queries) == 0


@pytest.mark.django_db
def test_surrogate_email_and_weak_password_are_reported_together():
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(DomainValidationError) as raised,
    ):
        register_user(email=SURROGATE_EMAIL, password=WEAK_PASSWORD)

    assert list(raised.value.message_dict) == ["email", "password"]
    assert codes_of(raised) == {
        "email": {"email_invalid"},
        "password": {"password_too_short"},
    }
    assert len(queries) == 0


@pytest.mark.django_db
def test_concurrent_duplicate_is_translated_to_email_taken(monkeypatch):
    User(email=EMAIL).save()
    skip_validation(monkeypatch)

    with pytest.raises(DomainValidationError) as raised:
        register_user(email="Ana@Correo.ES", password=PASSWORD)

    assert codes_of(raised) == {"email": {"email_taken"}}
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    # La conexión sigue usable tras el rollback del atomic
    assert User.objects.count() == 1
