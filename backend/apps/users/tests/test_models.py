from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import DataError, IntegrityError, transaction

from apps.core.text import reject_control_characters
from apps.users.models import User

EMAIL_SUFFIX = "@x.es"
EMAIL_KEY = "users_user_email_key"
EMAIL_LOWER_UNIQUE = "users_user_email_lower_unique"


def test_user_is_identified_by_email():
    assert User.USERNAME_FIELD == "email"
    assert User.EMAIL_FIELD == "email"
    assert User.REQUIRED_FIELDS == []


def test_user_has_no_username_field():
    with pytest.raises(FieldDoesNotExist):
        User._meta.get_field("username")


def test_user_model_is_the_configured_auth_model():
    assert settings.AUTH_USER_MODEL == "users.User"
    assert get_user_model() is User


def test_email_field_definition():
    field = User._meta.get_field("email")

    assert field.unique is True
    assert field.blank is False
    assert field.max_length == 254
    assert reject_control_characters in field.validators


def test_str_does_not_expose_the_email():
    user = User(pk=7, email="ana@correo.es")

    assert str(user) == "User 7"
    assert "ana" not in str(user)


@pytest.mark.django_db
def test_email_of_254_characters_is_saved():
    email = "a" * (254 - len(EMAIL_SUFFIX)) + EMAIL_SUFFIX

    with transaction.atomic():
        User(email=email).save()

    assert User.objects.filter(email=email).exists()


@pytest.mark.django_db
def test_email_of_255_characters_is_rejected_by_the_database():
    email = "a" * (255 - len(EMAIL_SUFFIX)) + EMAIL_SUFFIX

    with pytest.raises(DataError), transaction.atomic():
        User(email=email).save()


@pytest.mark.django_db
def test_emails_differing_only_in_case_are_rejected_by_the_database():
    User(email="Ana@Correo.ES").save()

    with pytest.raises(IntegrityError) as raised, transaction.atomic():
        User(email="ana@correo.es").save()

    assert raised.value.__cause__.diag.constraint_name == EMAIL_LOWER_UNIQUE


@pytest.mark.django_db
def test_exact_duplicate_email_is_rejected_by_the_database():
    User(email="ana@correo.es").save()

    with pytest.raises(IntegrityError) as raised, transaction.atomic():
        User(email="ana@correo.es").save()

    # Nombre automático de unique=True: el servicio lo traduce por este nombre
    assert raised.value.__cause__.diag.constraint_name == EMAIL_KEY


@pytest.mark.django_db
def test_dates_are_timezone_aware_in_utc():
    user = User(email="ana@correo.es")
    user.save()
    user.refresh_from_db()

    assert user.date_joined.utcoffset() == timedelta(0)
    assert user.last_login is None
