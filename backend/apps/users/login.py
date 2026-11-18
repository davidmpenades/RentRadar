from django.contrib.auth import authenticate
from django.views.decorators.debug import sensitive_variables

from apps.core.text import contains_lone_surrogate
from apps.users.services import PASSWORD_MAX_LENGTH


def is_queryable_email(email):
    # PostgreSQL rechaza el nulo y psycopg no codifica un sustituto suelto
    return (
        email is not None
        and email.strip() != ""
        and "\x00" not in email
        and not contains_lone_surrogate(email)
    )


def is_checkable_password(password):
    # El nulo sí se comprueba: no rompe el hash y puede ser parte de una contraseña
    return (
        password is not None
        and password != ""
        and len(password) <= PASSWORD_MAX_LENGTH
        and not contains_lone_surrogate(password)
    )


@sensitive_variables("email", "password")
def check_credentials(http_request, *, email, password):
    # Que se calcule un hash depende solo de la forma de lo recibido, no de la cuenta
    if not (is_queryable_email(email) and is_checkable_password(password)):
        return None
    # Email crudo: get_by_natural_key lo normaliza una sola vez, como la clave del par
    return authenticate(http_request, email=email, password=password)
