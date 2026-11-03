import json

import pytest
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import connection, transaction
from django.http import Http404
from rest_framework import exceptions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core.api import ERROR_CODES, ApiError, api_exception_handler

SECRET = "secret-value-49.123"


class Boom(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        raise ApiError("invalid_parameters", {"south": "not_a_number"})


class Fine(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"ok": True})


def call(view, method="get", path="/", **extra):
    request = getattr(APIRequestFactory(), method)(path, **extra)
    response = view.as_view()(request)
    response.render()
    return response


def body(response):
    return json.loads(response.content)


def test_the_set_of_codes_is_the_documented_table():
    assert {
        "invalid_parameters",
        "zone_inverted",
        "zone_too_large",
        "method_not_allowed",
        "throttled",
        "not_found",
        "forbidden",
        "bad_request",
    } == ERROR_CODES


def test_api_error_rejects_a_code_outside_the_table():
    with pytest.raises(ValueError):
        ApiError("made_up")


def test_api_error_without_params_has_only_the_code():
    response = api_exception_handler(ApiError("zone_inverted"), {})

    assert response.status_code == 400
    assert response.data == {"code": "zone_inverted"}
    assert response["Cache-Control"] == "no-store"


def test_api_error_with_params_lists_them():
    error = ApiError("invalid_parameters", {"south": "required", "east": "repeated"})

    response = api_exception_handler(error, {})

    assert response.status_code == 400
    assert response.data == {
        "code": "invalid_parameters",
        "params": {"south": "required", "east": "repeated"},
    }


def test_method_not_allowed_has_no_detail():
    response = api_exception_handler(exceptions.MethodNotAllowed("POST"), {})

    assert response.status_code == 405
    assert response.data == {"code": "method_not_allowed"}
    assert response["Cache-Control"] == "no-store"


def test_throttled_carries_retry_after_in_header_and_body():
    response = api_exception_handler(exceptions.Throttled(wait=12.3), {})

    assert response.status_code == 429
    assert response.data == {"code": "throttled", "retry_after": 13}
    assert response["Retry-After"] == "13"
    assert response["Cache-Control"] == "no-store"


def test_throttled_never_waits_less_than_one_second():
    response = api_exception_handler(exceptions.Throttled(wait=0.2), {})

    assert response.data["retry_after"] == 1
    assert response["Retry-After"] == "1"


def test_throttled_without_wait_still_gives_one_second():
    response = api_exception_handler(exceptions.Throttled(), {})

    assert response.data == {"code": "throttled", "retry_after": 1}
    assert response["Retry-After"] == "1"


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (exceptions.NotFound(), 404, "not_found"),
        (exceptions.NotAuthenticated(), 401, "forbidden"),
        (exceptions.PermissionDenied(), 403, "forbidden"),
        (exceptions.ParseError(), 400, "bad_request"),
        (exceptions.NotAcceptable(), 406, "bad_request"),
        (exceptions.UnsupportedMediaType("text/xml"), 415, "bad_request"),
    ],
)
def test_other_api_exceptions_get_a_general_code(exc, status, code):
    response = api_exception_handler(exc, {})

    assert response.status_code == status
    assert response.data == {"code": code}
    assert response["Cache-Control"] == "no-store"


def test_the_authenticate_header_chosen_by_drf_is_kept():
    exc = exceptions.NotAuthenticated()
    exc.auth_header = 'Bearer realm="api"'

    response = api_exception_handler(exc, {})

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == 'Bearer realm="api"'


@pytest.mark.django_db
def test_an_error_response_marks_the_atomic_request_for_rollback(monkeypatch):
    monkeypatch.setitem(connection.settings_dict, "ATOMIC_REQUESTS", True)
    with transaction.atomic():
        assert not transaction.get_rollback()

        api_exception_handler(ApiError("zone_inverted"), {})

        assert transaction.get_rollback()
        transaction.set_rollback(False)


def test_a_server_error_from_drf_is_left_to_django():
    assert api_exception_handler(exceptions.APIException(), {}) is None


@pytest.mark.parametrize("exc", [ValueError(SECRET), KeyError(SECRET)])
def test_exceptions_that_are_not_from_drf_are_left_to_django(exc):
    assert api_exception_handler(exc, {}) is None


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (Http404(SECRET), 404, "not_found"),
        (DjangoPermissionDenied(SECRET), 403, "forbidden"),
    ],
)
def test_django_not_found_and_permission_denied_get_the_uniform_format(
    exc, status, code
):
    response = api_exception_handler(exc, {})

    assert response.status_code == status
    assert response.data == {"code": code}
    assert response["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "exc",
    [
        exceptions.ValidationError({"south": [SECRET]}),
        exceptions.NotFound(SECRET),
        exceptions.MethodNotAllowed(SECRET, detail=SECRET),
        exceptions.Throttled(wait=3, detail=SECRET),
        exceptions.PermissionDenied(SECRET),
        Http404(SECRET),
        DjangoPermissionDenied(SECRET),
    ],
)
def test_the_body_never_repeats_a_received_value(exc):
    response = api_exception_handler(exc, {})

    assert SECRET not in json.dumps(response.data)
    assert "detail" not in response.data


def test_a_view_that_raises_api_error_answers_with_the_uniform_format():
    response = call(Boom)

    assert response.status_code == 400
    assert response["Content-Type"] == "application/json"
    assert body(response) == {
        "code": "invalid_parameters",
        "params": {"south": "not_a_number"},
    }
    assert response["Cache-Control"] == "no-store"


def test_a_disallowed_method_goes_through_the_handler():
    response = call(Fine, "post")

    assert response.status_code == 405
    assert body(response) == {"code": "method_not_allowed"}
    assert response["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "extra",
    [
        {"HTTP_ACCEPT": "application/xml"},
        {"HTTP_ACCEPT": "text/html"},
        {"HTTP_ACCEPT": "image/png;q=1, */*;q=0"},
    ],
)
def test_accept_is_ignored_and_the_answer_is_json(extra):
    response = call(Fine, **extra)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert body(response) == {"ok": True}


def test_format_query_parameter_is_ignored():
    response = call(Fine, path="/?format=xml")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"


def test_errors_are_json_even_when_the_client_asks_for_something_else():
    response = call(Boom, HTTP_ACCEPT="application/xml")

    assert response.status_code == 400
    assert response["Content-Type"] == "application/json"
    assert body(response)["code"] == "invalid_parameters"


def test_json_answers_do_not_vary_on_accept():
    response = call(Fine)

    assert "Accept" not in response.get("Vary", "")
