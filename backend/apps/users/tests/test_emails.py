import pytest

from apps.users.models import User, UserManager


@pytest.mark.parametrize(
    "raw",
    [
        " Ana@Correo.ES\n",
        "\tana@correo.es",
        "ana@correo.es\r\n",
        "\u00a0ana@correo.es\u00a0",
        "  ana@correo.es  ",
    ],
)
def test_normalize_email_strips_surrounding_whitespace(raw):
    assert UserManager.normalize_email(raw) == "ana@correo.es"


def test_normalize_email_lowercases_local_part_and_domain():
    assert UserManager.normalize_email("ANA.Lopez@CORREO.ES") == "ana.lopez@correo.es"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ａｎａ@correo.es", "ana@correo.es"),
        ("\ufb01na@correo.es", "fina@correo.es"),
    ],
)
def test_normalize_email_applies_nfkc(raw, expected):
    assert UserManager.normalize_email(raw) == expected


def test_normalize_email_applies_nfkc_before_lower():
    # NFKC convierte ℡ en «TEL»: si lower() fuera antes, quedaría en mayúsculas
    assert UserManager.normalize_email("℡@correo.es") == "tel@correo.es"


@pytest.mark.parametrize(
    "raw", [" Ana@Correo.ES\n", "ａｎａ@CORREO.ES", "℡@correo.es", "ana@correo.es"]
)
def test_normalize_email_is_idempotent(raw):
    once = UserManager.normalize_email(raw)
    assert UserManager.normalize_email(once) == once


def test_normalize_email_is_available_from_the_manager_instance():
    assert User.objects.normalize_email(" ANA@correo.es ") == "ana@correo.es"


@pytest.mark.django_db
def test_get_by_natural_key_normalizes_the_email():
    user = User(email="ana@correo.es")
    user.save()

    assert User.objects.get_by_natural_key(" ANA@Correo.ES\n") == user


@pytest.mark.django_db
def test_get_by_natural_key_does_not_find_other_emails():
    User(email="ana@correo.es").save()

    with pytest.raises(User.DoesNotExist):
        User.objects.get_by_natural_key("otra@correo.es")
