from unittest import mock

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import path

from apps.core.middleware import (
    CleanMarkedResponseMiddleware,
    mark_response_cookieless,
)

MIDDLEWARE_PATH = "apps.core.middleware.CleanMarkedResponseMiddleware"
MALFORMED_COOKIES = {"csrftoken": "x", "sessionid": "short"}


def marked_view(request, status=200):
    return mark_response_cookieless(HttpResponse("marked", status=status))


def unmarked_view(request):
    return HttpResponse("unmarked")


urlpatterns = [
    path("marked/", marked_view),
    path("marked/<int:status>/", marked_view),
    path("unmarked/", unmarked_view),
]


def run_middleware(response, request_path="/"):
    middleware = CleanMarkedResponseMiddleware(lambda request: response)
    return middleware(RequestFactory().get(request_path))


def response_with_cookies(vary=None):
    response = HttpResponse("body")
    response.set_cookie("csrftoken", "token")
    response.set_cookie("sessionid", "session")
    response.set_cookie("other", "value")
    if vary is not None:
        response["Vary"] = vary
    return response


def set_malformed_cookies(client):
    for name, value in MALFORMED_COOKIES.items():
        client.cookies[name] = value


class ForbiddenAccessRequest:
    @property
    def session(self):
        raise AssertionError("El middleware no debe leer request.session")

    @property
    def user(self):
        raise AssertionError("El middleware no debe leer request.user")


# A) Unitarios con un get_response falso


def test_mark_response_cookieless_returns_same_response_marked_true():
    response = HttpResponse()

    result = mark_response_cookieless(response)

    assert result is response
    assert response.cookieless is True


def test_marked_response_leaves_without_cookies():
    response = mark_response_cookieless(response_with_cookies())

    result = run_middleware(response)

    assert result is response
    assert len(result.cookies) == 0
    assert not any(h.lower() == "set-cookie" for h in result.headers)


def test_unmarked_response_keeps_all_its_cookies_and_vary():
    response = response_with_cookies(vary="Accept-Encoding, Cookie")

    result = run_middleware(response)

    assert sorted(result.cookies) == ["csrftoken", "other", "sessionid"]
    assert result.cookies["other"].value == "value"
    assert result["Vary"] == "Accept-Encoding, Cookie"


@pytest.mark.parametrize("mark", [1, "yes", "True", [0], object()])
def test_truthy_but_not_true_mark_does_not_clean_the_response(mark):
    response = response_with_cookies(vary="Cookie")
    response.cookieless = mark

    result = run_middleware(response)

    assert sorted(result.cookies) == ["csrftoken", "other", "sessionid"]
    assert result["Vary"] == "Cookie"


@pytest.mark.parametrize(
    ("vary", "expected"),
    [
        ("Cookie", None),
        ("Accept-Encoding, Cookie", "Accept-Encoding"),
        ("Cookie, Accept-Encoding", "Accept-Encoding"),
        ("cookie", None),
        ("COOKIE", None),
        ("  Accept-Encoding  ,   cookie  ,Origin ", "Accept-Encoding, Origin"),
        ("Cookie,Cookie", None),
        ("Accept-Encoding", "Accept-Encoding"),
        ("Accept-Encoding, Origin", "Accept-Encoding, Origin"),
        ("Cookies", "Cookies"),
    ],
    ids=[
        "only-cookie",
        "cookie-last",
        "cookie-first",
        "lowercase",
        "uppercase",
        "odd-spaces",
        "repeated",
        "no-cookie-single",
        "no-cookie-several",
        "similar-name-kept",
    ],
)
def test_marked_response_removes_only_the_cookie_token_from_vary(vary, expected):
    response = mark_response_cookieless(response_with_cookies(vary=vary))

    result = run_middleware(response)

    if expected is None:
        assert "Vary" not in result
    else:
        assert result["Vary"] == expected


def test_marked_response_without_vary_nor_cookies_stays_the_same():
    response = mark_response_cookieless(HttpResponse("body", status=204))

    result = run_middleware(response)

    assert result is response
    assert "Vary" not in result
    assert len(result.cookies) == 0
    assert result.status_code == 204
    assert result.content == b"body"


@pytest.mark.parametrize(
    "request_path",
    ["/", "/api/v1/public/assets/", "/admin/", "/api/v1/other/"],
    ids=["root", "public-api", "admin", "other-api"],
)
def test_cleaning_does_not_depend_on_the_request_path(request_path):
    response = mark_response_cookieless(response_with_cookies(vary="Cookie"))

    result = run_middleware(response, request_path)

    assert len(result.cookies) == 0
    assert "Vary" not in result


def test_unmarked_response_under_api_keeps_its_cookies_and_vary():
    response = response_with_cookies(vary="Cookie")

    result = run_middleware(response, "/api/v1/public/assets/")

    assert sorted(result.cookies) == ["csrftoken", "other", "sessionid"]
    assert result["Vary"] == "Cookie"


def test_middleware_never_reads_session_nor_user():
    marked = mark_response_cookieless(response_with_cookies(vary="Cookie"))
    unmarked = response_with_cookies(vary="Cookie")

    for response in (marked, unmarked):
        middleware = CleanMarkedResponseMiddleware(lambda request, r=response: r)
        middleware(ForbiddenAccessRequest())

    assert len(marked.cookies) == 0
    assert len(unmarked.cookies) == 3


# B) Integración con la pila real, sin BD (sin django_db)


@pytest.fixture
def stack_client(client, settings):
    settings.ROOT_URLCONF = __name__
    set_malformed_cookies(client)
    return client


def set_cookie_headers(response):
    return response.cookies.output()


def test_unmarked_view_with_malformed_cookies_does_set_cookies_and_vary(stack_client):
    response = stack_client.get("/unmarked/")

    assert "csrftoken" in response.cookies
    assert response.cookies["csrftoken"].value != "x"
    assert "sessionid" in response.cookies
    assert response.cookies["sessionid"]["max-age"] == 0
    assert "Cookie" in response["Vary"]


def test_marked_view_with_malformed_cookies_leaves_without_cookies_nor_vary(
    stack_client,
):
    response = stack_client.get("/marked/")

    assert response.status_code == 200
    assert set_cookie_headers(response) == ""
    assert len(response.cookies) == 0
    assert "Vary" not in response


@pytest.mark.parametrize(
    "method", ["get", "head", "post", "put", "patch", "delete", "options"]
)
def test_marked_view_leaves_without_cookies_for_every_method(stack_client, method):
    response = getattr(stack_client, method)("/marked/")

    assert len(response.cookies) == 0
    assert "Vary" not in response


@pytest.mark.parametrize("status", [400, 405, 429])
@pytest.mark.parametrize("method", ["get", "post", "options"])
def test_marked_error_responses_leave_without_cookies_nor_vary(
    stack_client, method, status
):
    response = getattr(stack_client, method)(f"/marked/{status}/")

    assert response.status_code == status
    assert len(response.cookies) == 0
    assert "Vary" not in response


def test_marked_view_does_not_load_the_session(stack_client):
    with mock.patch.object(
        SessionStore, "load", side_effect=AssertionError("Sesión cargada")
    ) as load:
        response = stack_client.get("/marked/")

    assert response.status_code == 200
    load.assert_not_called()


# C) Configuración


def test_middleware_is_first_and_session_and_csrf_come_after(settings):
    middleware = settings.MIDDLEWARE

    assert middleware[0] == MIDDLEWARE_PATH
    assert middleware.index("django.contrib.sessions.middleware.SessionMiddleware") > 0
    assert middleware.index("django.middleware.csrf.CsrfViewMiddleware") > 0
