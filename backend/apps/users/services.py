from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from apps.core.db import CONSTRAINT_VIOLATED, run_guarded
from apps.core.errors import (
    UNMAPPED_ERROR,
    DomainValidationError,
    translate_validation_error,
)
from apps.users.models import User

EMAIL_EMPTY = "email_empty"
EMAIL_INVALID = "email_invalid"
EMAIL_CONTROL_CHAR = "email_control_char"
EMAIL_TOO_LONG = "email_too_long"
EMAIL_TAKEN = "email_taken"
PASSWORD_REQUIRED = "password_required"
PASSWORD_INVALID = "password_invalid"
PASSWORD_TOO_LONG = "password_too_long"
VALIDATION_FAILED = UNMAPPED_ERROR[1]

ERROR_CODES = frozenset(
    {
        EMAIL_EMPTY,
        EMAIL_INVALID,
        EMAIL_CONTROL_CHAR,
        EMAIL_TOO_LONG,
        EMAIL_TAKEN,
        PASSWORD_REQUIRED,
        PASSWORD_INVALID,
        PASSWORD_TOO_LONG,
        CONSTRAINT_VIOLATED,
        VALIDATION_FAILED,
    }
)

PASSWORD_MAX_LENGTH = 128

# Al cambiar el email solo se valida ese campo: los demás no se tocan
NON_EMAIL_FIELDS = frozenset(
    field.name for field in User._meta.fields if field.name != "email"
)

# (campo, código de Django) -> (campo, código de dominio)
DJANGO_CODES = {
    ("email", "blank"): ("email", EMAIL_EMPTY),
    ("email", "invalid"): ("email", EMAIL_INVALID),
    ("email", "control_char"): ("email", EMAIL_CONTROL_CHAR),
    ("email", "max_length"): ("email", EMAIL_TOO_LONG),
    ("email", "unique"): ("email", EMAIL_TAKEN),
    (NON_FIELD_ERRORS, EMAIL_TAKEN): ("email", EMAIL_TAKEN),
}

CONSTRAINT_CODES = {
    "users_user_email_key": ("email", EMAIL_TAKEN),
    "users_user_email_lower_unique": ("email", EMAIL_TAKEN),
}


def create_user(*, email, password):
    return _create_account(email, password, is_admin=False)


def create_superuser(*, email, password):
    return _create_account(email, password, is_admin=True)


def change_user_email(*, user, email):
    previous_email = user.email
    errors = {}
    if isinstance(email, str) or email is None:
        user.email = User.objects.normalize_email(email or "")
        errors.update(_validation_errors(user, exclude=NON_EMAIL_FIELDS))
        if not errors:
            _, errors = run_guarded(
                lambda: user.save(update_fields=["email"]), CONSTRAINT_CODES
            )
    else:
        errors["email"] = [EMAIL_INVALID]
    if errors:
        user.email = previous_email
        raise DomainValidationError(errors)
    return user


def _create_account(email, password, *, is_admin):
    errors = {}
    if isinstance(email, str) or email is None:
        user = User(
            email=User.objects.normalize_email(email or ""),
            is_staff=is_admin,
            is_superuser=is_admin,
        )
        errors.update(_validation_errors(user, exclude={"password"}))
    else:
        errors["email"] = [EMAIL_INVALID]
    password_code = _password_error(password)
    if password_code:
        errors["password"] = [password_code]
    if not errors:
        user.set_password(password)
        _, errors = run_guarded(user.save, CONSTRAINT_CODES)
    if errors:
        raise DomainValidationError(errors)
    return user


def _password_error(password):
    if password is None or password == "":
        return PASSWORD_REQUIRED
    if not isinstance(password, str):
        return PASSWORD_INVALID
    if len(password) > PASSWORD_MAX_LENGTH:
        return PASSWORD_TOO_LONG
    return None


def _validation_errors(user, *, exclude):
    try:
        user.full_clean(exclude=exclude)
    except ValidationError as exc:
        return translate_validation_error(exc, DJANGO_CODES)
    return {}
