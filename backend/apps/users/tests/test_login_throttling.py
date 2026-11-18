import json

import pytest
from django.conf import settings as django_settings
from django.core.cache import caches
from django.test import RequestFactory
from rest_framework.request import Request

from apps.users.models import User
from apps.users.tests.helpers import Clock
from apps.users.throttling import (
    LOGIN_CACHE_ALIAS,
    LoginIpThrottle,
    client_bucket,
    wait_seconds,
)

PATH = "/login-like/"
SESSION_PATH = "/login-like-session/"
LIMIT = 20
MINUTE = 60
JSON = "application/json"
LOCMEM = "django.core.cache.backends.locmem.LocMemCache"
TOKEN = "a1B2c3D4" * 4
BODY = json.dumps({"email": "ana@correo.es", "password": "a-long-enough-one"})
IP = "203.0.113.7"
CACHE_KEY = f"throttle_login_ip_{IP}"


@pytest.fixture(autouse=True)
def test_urls(settings):
    settings.ROOT_URLCONF = "apps.users.tests.throttle_urls"


@pytest.fixture
def clock(monkeypatch):
    fake = Clock()
    # staticmethod: sin él Python pasaría la instancia como primer argumento
    monkeypatch.setattr(LoginIpThrottle, "timer", staticmethod(fake))
    return fake


def post(client, body=BODY, *, token=TOKEN, ip=IP, path=PATH, **extra):
    client.cookies[django_settings.CSRF_COOKIE_NAME] = TOKEN
    headers = {} if token is None else {"X-CSRFToken": token}
    return client.post(
        path,
        data=body,
        content_type=JSON,
        headers=headers,
        REMOTE_ADDR=ip,
        **extra,
    )


def fill_the_quota(client, **kwargs):
    for _ in range(LIMIT):
        assert post(client, **kwargs).status_code == 200


def assert_throttled(response):
    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "throttled"
    assert isinstance(body["retry_after"], int)
    assert body["retry_after"] >= 1
    assert response["Retry-After"] == str(body["retry_after"])
    return body["retry_after"]


# wait_seconds: el historial va de la anotación más reciente a la más antigua


def test_wait_seconds_counts_from_the_oldest_entry_with_exactly_the_limit():
    history = [1000.0 - second for second in range(20)]

    assert wait_seconds(history, 1000.0, LIMIT, MINUTE) == 41


def test_wait_seconds_counts_from_the_entry_that_leaves_the_count_below_the_limit():
    # Con 23 anotaciones, la que cuenta es la 20.ª, no la más antigua (38 s)
    history = [1000.0 - second for second in range(23)]

    assert wait_seconds(history, 1000.0, LIMIT, MINUTE) == 41


def test_wait_seconds_rounds_up_and_is_at_least_one():
    assert wait_seconds([1000.0] * 20, 1000.0, LIMIT, MINUTE) == 60
    assert wait_seconds([999.4] * 20, 1000.0, LIMIT, MINUTE) == 60
    assert wait_seconds([940.2] * 20, 1000.0, LIMIT, MINUTE) == 1
    assert wait_seconds([940.0] * 20, 1000.0, LIMIT, MINUTE) == 1


# identidad del visitante y clave del contador


def test_the_login_limit_is_declared_on_the_class():
    assert LoginIpThrottle.rate == "20/min"
    assert LoginIpThrottle.scope == "login_ip"
    assert LoginIpThrottle().num_requests == LIMIT
    assert LoginIpThrottle().duration == MINUTE


def test_the_cache_key_carries_the_scope_and_the_bucket_only():
    marker = "marker-9f3a"
    request = Request(RequestFactory().post(PATH, REMOTE_ADDR=marker))

    key = LoginIpThrottle().get_cache_key(request, None)

    assert key == "throttle_login_ip_unknown"
    assert marker not in key


def test_the_cache_key_of_a_valid_address_uses_its_bucket():
    request = Request(RequestFactory().post(PATH, REMOTE_ADDR="2001:db8:0:1::9"))

    assert LoginIpThrottle().get_cache_key(request, None) == (
        "throttle_login_ip_2001:db8:0:1::/64"
    )


def test_client_bucket_is_the_bucket_of_remote_addr():
    request = Request(RequestFactory().post(PATH, REMOTE_ADDR="2001:db8:0:1::9"))

    assert client_bucket(request) == "2001:db8:0:1::/64"


def test_client_bucket_ignores_x_forwarded_for():
    request = Request(
        RequestFactory().post(
            PATH,
            REMOTE_ADDR=IP,
            HTTP_X_FORWARDED_FOR="198.51.100.9, 192.0.2.1",
        )
    )

    assert client_bucket(request) == IP


def test_client_bucket_sends_anything_that_is_not_an_address_to_the_fixed_bucket():
    request = Request(RequestFactory().post(PATH, REMOTE_ADDR="not an address"))

    assert client_bucket(request) == "unknown"


def test_the_limit_uses_the_client_bucket_for_its_key():
    request = Request(RequestFactory().post(PATH, REMOTE_ADDR="2001:db8:0:1::9"))

    key = LoginIpThrottle().get_cache_key(request, None)

    assert key == f"throttle_login_ip_{client_bucket(request)}"


# almacén


def test_the_counters_live_in_the_login_cache_and_not_in_default(csrf_client, clock):
    assert post(csrf_client).status_code == 200

    assert caches[LOGIN_CACHE_ALIAS].get(CACHE_KEY) == [clock.now]
    assert caches["default"].get(CACHE_KEY) is None


def test_the_cache_is_resolved_at_each_use_and_follows_override_settings(settings):
    before = LoginIpThrottle().cache
    other = {"BACKEND": LOCMEM, "LOCATION": "another-store"}

    settings.CACHES = {**settings.CACHES, LOGIN_CACHE_ALIAS: other}
    after = LoginIpThrottle().cache

    assert after is caches[LOGIN_CACHE_ALIAS]
    assert after is not before


# límite sobre una vista


def test_twenty_requests_pass_and_the_twenty_first_is_throttled(csrf_client, clock):
    fill_the_quota(csrf_client)

    response = post(csrf_client)

    assert assert_throttled(response) == MINUTE


def test_the_wait_shrinks_as_the_clock_advances(csrf_client, clock):
    fill_the_quota(csrf_client)
    clock.advance(10)

    assert assert_throttled(post(csrf_client)) == MINUTE - 10


def test_the_wait_comes_from_the_entry_that_leaves_the_count_below_the_limit(
    csrf_client, clock
):
    # 23 anotaciones, de 1000 hacia atrás de 2 en 2: la 20.ª es 962 y la última, 956
    # DRF devolvería None (retry_after 1) y la más antigua daría 16
    marks = [clock.now - 2 * step for step in range(23)]
    caches[LOGIN_CACHE_ALIAS].set(CACHE_KEY, marks, MINUTE)

    assert assert_throttled(post(csrf_client)) == 22


COUNTED = {
    "invalid-json": lambda c: post(c, "{not json"),
    "wrong-types": lambda c: post(c, '{"email": 5}'),
    "root-list": lambda c: post(c, "[]"),
    "too-large-declared": lambda c: post(c, "{" + " " * 5000 + "}"),
    "transfer-encoding": lambda c: post(c, "{}", HTTP_TRANSFER_ENCODING="chunked"),
    "csrf-rejected": lambda c: post(c, token=None),
    "csrf-mismatch": lambda c: post(c, token="x" * 32),
    "put": lambda c: c.put(PATH, data=BODY, content_type=JSON, REMOTE_ADDR=IP),
    "head": lambda c: c.head(PATH, REMOTE_ADDR=IP),
    "options": lambda c: c.options(PATH, REMOTE_ADDR=IP),
    "get": lambda c: c.get(PATH, REMOTE_ADDR=IP),
}


@pytest.mark.parametrize("send", COUNTED.values(), ids=COUNTED.keys())
def test_every_kind_of_request_counts_whatever_the_answer(csrf_client, clock, send):
    for _ in range(LIMIT):
        assert send(csrf_client).status_code != 429

    assert_throttled(post(csrf_client))


def test_the_counted_requests_really_answer_with_their_own_errors(csrf_client, clock):
    assert post(csrf_client, "{not json").json() == {"code": "invalid_request"}
    assert post(csrf_client, "{" + " " * 5000 + "}").status_code == 413
    assert post(csrf_client, "{}", HTTP_TRANSFER_ENCODING="chunked").status_code == 413
    assert post(csrf_client, token=None).json() == {"code": "csrf_failed"}
    assert csrf_client.put(PATH, REMOTE_ADDR=IP).status_code == 405
    assert csrf_client.head(PATH, REMOTE_ADDR=IP).status_code == 405
    assert csrf_client.options(PATH, REMOTE_ADDR=IP).status_code == 405


def test_throttled_requests_do_not_count_and_do_not_extend_the_wait(csrf_client, clock):
    fill_the_quota(csrf_client)
    clock.advance(10)
    first = assert_throttled(post(csrf_client))
    for _ in range(25):
        clock.advance(1)
        assert post(csrf_client).status_code == 429
    clock.advance(MINUTE - 10 - 25)

    assert first == MINUTE - 10
    assert post(csrf_client).status_code == 200


def test_the_limit_comes_before_csrf_and_before_the_method(csrf_client, clock):
    fill_the_quota(csrf_client)

    assert_throttled(post(csrf_client, token=None))
    assert_throttled(post(csrf_client, token="x" * 32))
    assert_throttled(
        csrf_client.put(PATH, data=BODY, content_type=JSON, REMOTE_ADDR=IP)
    )
    head = csrf_client.head(PATH, REMOTE_ADDR=IP)
    assert head.status_code == 429
    assert int(head["Retry-After"]) >= 1
    assert_throttled(csrf_client.options(PATH, REMOTE_ADDR=IP))


def test_the_limit_comes_before_reading_the_body(csrf_client, clock):
    fill_the_quota(csrf_client)

    assert_throttled(post(csrf_client, "{" + " " * 5000 + "}"))
    assert_throttled(post(csrf_client, "{}", HTTP_TRANSFER_ENCODING="chunked"))


def test_x_forwarded_for_is_ignored(csrf_client, clock):
    for index in range(LIMIT):
        response = post(csrf_client, HTTP_X_FORWARDED_FOR=f"198.51.100.{index}")
        assert response.status_code == 200

    assert_throttled(post(csrf_client, HTTP_X_FORWARDED_FOR="198.51.100.200"))
    assert_throttled(post(csrf_client, HTTP_X_FORWARDED_FOR="2001:db8::1, 10.0.0.1"))
    assert_throttled(post(csrf_client, HTTP_X_FORWARDED_FOR="unknown"))


def test_another_remote_addr_has_its_own_quota(csrf_client, clock):
    fill_the_quota(csrf_client)

    assert_throttled(post(csrf_client))
    assert post(csrf_client, ip="203.0.113.8").status_code == 200


def test_two_addresses_of_the_same_64_share_the_limit(csrf_client, clock):
    for index in range(LIMIT):
        assert post(csrf_client, ip=f"2001:db8:0:1::{index + 1}").status_code == 200

    assert_throttled(post(csrf_client, ip="2001:db8:0:1:ffff::1"))


def test_an_address_of_another_64_has_its_own_quota(csrf_client, clock):
    fill_the_quota(csrf_client, ip="2001:db8:0:1::1")

    assert_throttled(post(csrf_client, ip="2001:db8:0:1::2"))
    assert post(csrf_client, ip="2001:db8:0:2::1").status_code == 200


def test_unusable_addresses_share_the_fixed_bucket_without_failing(csrf_client, clock):
    for index in range(LIMIT):
        assert post(csrf_client, ip=f"garbage-{index}").status_code == 200

    assert_throttled(post(csrf_client, ip="other garbage"))
    assert_throttled(post(csrf_client, ip=""))
    assert post(csrf_client, ip=IP).status_code == 200


def test_the_window_frees_up_as_the_clock_advances(csrf_client, clock):
    fill_the_quota(csrf_client)
    assert_throttled(post(csrf_client))

    clock.advance(MINUTE - 1)
    assert_throttled(post(csrf_client))
    clock.advance(1)

    assert post(csrf_client).status_code == 200


def test_the_window_slides_instead_of_resetting(csrf_client, clock):
    for _ in range(10):
        assert post(csrf_client).status_code == 200
    clock.advance(MINUTE // 2)
    for _ in range(10):
        assert post(csrf_client).status_code == 200
    assert_throttled(post(csrf_client))

    clock.advance(MINUTE // 2)
    # Las 10 del segundo 0 ya salieron de la ventana y las 10 del 30 siguen dentro
    for _ in range(10):
        assert post(csrf_client).status_code == 200

    assert_throttled(post(csrf_client))


@pytest.mark.django_db
def test_a_logged_in_visitor_is_limited_too(csrf_client, clock):
    user = User.objects.create(email="ana@correo.es")
    csrf_client.force_login(user)
    fill_the_quota(csrf_client, path=SESSION_PATH)

    assert_throttled(post(csrf_client, path=SESSION_PATH))
