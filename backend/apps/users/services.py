from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError, transaction

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
CONSTRAINT_VIOLATED = "constraint_violated"
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
    errors = {}
    if isinstance(email, str) or email is None:
        user = User(email=User.objects.normalize_email(email or ""))
        errors.update(_validation_errors(user))
    else:
        errors["email"] = [EMAIL_INVALID]
    password_code = _password_error(password)
    if password_code:
        errors["password"] = [password_code]
    if errors:
        raise DomainValidationError(errors)
    user.set_password(password)
    _save_guarded(user)
    return user


def _password_error(password):
    if password is None or password == "":
        return PASSWORD_REQUIRED
    if not isinstance(password, str):
        return PASSWORD_INVALID
    if len(password) > PASSWORD_MAX_LENGTH:
        return PASSWORD_TOO_LONG
    return None


def _validation_errors(user):
    try:
        user.full_clean(exclude={"password"})
    except ValidationError as exc:
        return translate_validation_error(exc, DJANGO_CODES)
    return {}


def _save_guarded(instance):
    violated = None
    try:
        with transaction.atomic():
            instance.save()
    except IntegrityError as exc:
        violated = _constraint_name(exc)
    # El raise va fuera del except: así el error no encadena el original (RF-12)
    if violated is not None:
        raise DomainValidationError(_codes_for_constraint(violated))


def _constraint_name(error):
    diag = getattr(error.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) or ""


def _codes_for_constraint(name):
    field, code = CONSTRAINT_CODES.get(name, (NON_FIELD_ERRORS, CONSTRAINT_VIOLATED))
    return {field: [code]}
