import json
import logging
from unittest import mock
from urllib.parse import urlencode

import pytest
from django.conf import settings as django_settings
from django.core.handlers.wsgi import LimitedStream
from django.middleware.csrf import get_token
from django.test import RequestFactory

from apps.core.api import ApiError
from apps.core.csrf import enforce_csrf


def new_token():
    # API pública: devuelve el token enmascarado y deja el secreto en META
    request = RequestFactory().get("/")
    masked = get_token(request)
    return request.META["CSRF_COOKIE"], masked


# El secreto de 32 caracteres y su forma enmascarada de 64
TOKEN, MASKED = new_token()
OTHER_TOKEN, _ = new_token()
BODY = json.dumps({"email": "ana@correo.es", "password": "a-long-enough-one"})
JSON = "application/json"
FORM = "application/x-www-form-urlencoded"


@pytest.fixture(autouse=True)
def test_urls(settings):
    settings.ROOT_URLCONF = "apps.core.tests.csrf_urls"


def send(client, path="/post-only/", method="post", cookie=TOKEN, header=TOKEN):
    if cookie is not None:
        client.cookies[django_settings.CSRF_COOKIE_NAME] = cookie
    headers = {} if header is None else {"X-CSRFToken": header}
    if method in ("get", "head"):
        return getattr(client, method)(path, headers=headers)
    return getattr(client, method)(path, data=BODY, content_type=JSON, headers=headers)


def assert_csrf_rejected(response):
    assert response.status_code == 403
    assert json.loads(response.content) == {"code": "csrf_failed"}
    assert response["Cache-Control"] == "no-store"


REJECTED = {
    "no-header": {"header": None},
    "empty-header": {"header": ""},
    "no-cookie": {"cookie": None},
    "header-differs-from-cookie": {"header": OTHER_TOKEN},
    "cookie-of-31-characters": {"cookie": TOKEN[:31], "header": TOKEN[:31]},
    "cookie-of-33-characters": {"cookie": TOKEN + "a", "header": TOKEN + "a"},
    "cookie-of-63-characters": {"cookie": MASKED[:63], "header": MASKED[:63]},
    "cookie-of-65-characters": {"cookie": MASKED + "a", "header": MASKED + "a"},
    "cookie-with-symbols": {"cookie": "!" * 32, "header": "!" * 32},
}


@pytest.mark.parametrize("variant", REJECTED.values(), ids=REJECTED.keys())
def test_a_request_without_a_valid_token_gets_csrf_failed(csrf_client, variant):
    response = send(csrf_client, **variant)

    assert_csrf_rejected(response)


def test_a_foreign_origin_with_a_valid_token_is_rejected(csrf_client):
    csrf_client.cookies[django_settings.CSRF_COOKIE_NAME] = TOKEN

    response = csrf_client.post(
        "/post-only/",
        data=BODY,
        content_type=JSON,
        headers={"X-CSRFToken": TOKEN, "Origin": "http://evil.test"},
    )

    assert_csrf_rejected(response)


@pytest.mark.parametrize("variant", REJECTED.values(), ids=REJECTED.keys())
def test_the_rejection_never_shows_the_reason_nor_the_values(
    csrf_client, caplog, variant
):
    caplog.set_level(logging.DEBUG)

    response = send(csrf_client, **variant)

    shown = (response.content.decode() + caplog.text).lower()
    for fragment in ("csrf token", "csrf cookie", "origin checking", "incorrect"):
        assert fragment not in shown
    for value in (TOKEN, OTHER_TOKEN, "ana@correo.es", "a-long-enough-one"):
        assert value.lower() not in shown


def test_a_valid_token_lets_the_request_through(csrf_client):
    response = send(csrf_client)

    assert response.status_code == 200
    assert response.json() == {
        "email": "ana@correo.es",
        "password": "a-long-enough-one",
    }


def test_a_valid_masked_token_in_the_header_is_accepted(csrf_client):
    response = send(csrf_client, header=MASKED)

    assert response.status_code == 200


def test_the_body_is_never_read_to_decide(csrf_client):
    with mock.patch.object(LimitedStream, "read", side_effect=AssertionError):
        response = send(csrf_client, header=None)

    assert_csrf_rejected(response)


def test_a_form_body_is_never_parsed_to_decide(csrf_client):
    with mock.patch.object(LimitedStream, "read", side_effect=AssertionError):
        csrf_client.cookies[django_settings.CSRF_COOKIE_NAME] = TOKEN
        response = csrf_client.post(
            "/post-only/",
            data=urlencode({"csrfmiddlewaretoken": TOKEN}),
            content_type=FORM,
        )

    assert_csrf_rejected(response)


def test_the_token_in_a_form_field_does_not_count(csrf_client):
    csrf_client.cookies[django_settings.CSRF_COOKIE_NAME] = TOKEN

    response = csrf_client.post(
        "/post-only/",
        data=urlencode({"csrfmiddlewaretoken": TOKEN}),
        content_type=FORM,
    )

    assert_csrf_rejected(response)


@pytest.mark.parametrize("method", ["put", "patch", "delete", "head", "options"])
def test_a_method_the_view_does_not_serve_gets_405_not_403(csrf_client, method):
    response = send(csrf_client, method=method, header=None)

    assert response.status_code == 405
    assert response["Allow"] == "POST"
    assert response["Cache-Control"] == "no-store"
    if method != "head":
        assert json.loads(response.content) == {"code": "method_not_allowed"}


def test_a_method_without_a_handler_gets_405_even_if_the_class_lists_it(csrf_client):
    response = send(csrf_client, "/post-handler/", method="put", header=None)

    assert response.status_code == 405
    assert json.loads(response.content) == {"code": "method_not_allowed"}


def test_the_handler_of_a_listed_method_is_still_protected(csrf_client):
    response = send(csrf_client, "/post-handler/", header=None)

    assert_csrf_rejected(response)


def test_a_safe_method_needs_no_token(csrf_client):
    response = send(csrf_client, "/get-and-post/", method="get", header=None)

    assert response.status_code == 200


def test_the_post_of_the_same_view_does_need_it(csrf_client):
    response = send(csrf_client, "/get-and-post/", header=None)

    assert_csrf_rejected(response)


@pytest.mark.parametrize("method", ["post", "put"])
def test_the_throttle_answers_before_csrf(csrf_client, method):
    response = send(csrf_client, "/throttled/", method=method, header=None)

    assert response.status_code == 429
    assert json.loads(response.content) == {"code": "throttled", "retry_after": 3}
    assert response["Retry-After"] == "3"


def test_the_csrf_check_comes_before_the_body_is_read(csrf_client):
    with mock.patch.object(LimitedStream, "read", side_effect=AssertionError):
        response = csrf_client.post("/post-only/", data="{ not json", content_type=JSON)

    assert_csrf_rejected(response)


def test_the_mixin_leaves_other_views_alone(csrf_client, settings):
    settings.ROOT_URLCONF = "config.urls"

    response = csrf_client.post("/api/v1/public/assets/", data="{}", content_type=JSON)

    assert response.status_code == 405
    assert json.loads(response.content) == {"code": "method_not_allowed"}


def unchecked_request(**extra):
    request = RequestFactory().post("/x/", data=BODY, content_type=JSON, **extra)
    # RequestFactory marca la petición como exenta de CSRF
    request._dont_enforce_csrf_checks = False
    return request


def test_enforce_csrf_raises_without_context_or_reason():
    with pytest.raises(ApiError) as excinfo:
        enforce_csrf(unchecked_request())

    error = excinfo.value
    assert error.error_code == "csrf_failed"
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.params == {}
    assert str(error.detail) == "csrf_failed"


def test_enforce_csrf_accepts_a_matching_token():
    request = unchecked_request(HTTP_X_CSRFTOKEN=TOKEN)
    request.COOKIES[django_settings.CSRF_COOKIE_NAME] = TOKEN

    enforce_csrf(request)
