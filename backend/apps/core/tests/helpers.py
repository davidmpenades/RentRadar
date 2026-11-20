import pytest
from django.conf import settings
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

# Bien formada (32 caracteres de a-z y 0-9) y sin fila en la BD
KEY_WITHOUT_ROW = "0123456789abcdefghijklmnopqrstuv"

# Todas pasan la validación propia de Django, que solo pide 8 caracteres o más
MALFORMED_SESSION_VALUES = {
    "null-characters": chr(0) * 8,
    "31-characters": KEY_WITHOUT_ROW[:31],
    "33-characters": KEY_WITHOUT_ROW + "w",
    "uppercase": KEY_WITHOUT_ROW.upper(),
    "non-ascii": KEY_WITHOUT_ROW[:31] + chr(0xF1),
}

EACH_MALFORMED_SESSION_VALUE = pytest.mark.parametrize(
    "value", MALFORMED_SESSION_VALUES.values(), ids=MALFORMED_SESSION_VALUES.keys()
)


def octal_escaped(value):
    # Tres cifras octales: solo sirve para puntos de código menores que 256
    return "".join(
        char if char.isascii() and char.isalnum() else f"\\{ord(char):03o}"
        for char in value
    )


def raw_cookie_header(**cookies):
    # SimpleCookie rechaza los caracteres de control: la cabecera se escribe a mano
    return "; ".join(
        f'{name}="{octal_escaped(value)}"' for name, value in cookies.items()
    )


def post_with_raw_cookie(url, body, *, csrf_cookie, csrf_header, session_cookie):
    # Un error del servidor tiene que llegar como 500, no como excepción
    client = Client(enforce_csrf_checks=True, raise_request_exception=False)
    headers = {} if csrf_header is None else {"X-CSRFToken": csrf_header}
    cookie = raw_cookie_header(csrftoken=csrf_cookie, sessionid=session_cookie)
    with CaptureQueriesContext(connection) as captured:
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            headers=headers,
            HTTP_COOKIE=cookie,
        )
    return response, captured


def session_queries_with(captured, value):
    return [
        query["sql"]
        for query in captured.captured_queries
        if "django_session" in query["sql"] and value in query["sql"]
    ]


def assert_session_cookie_deleted(response):
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie.value == ""
    assert cookie["max-age"] == 0
