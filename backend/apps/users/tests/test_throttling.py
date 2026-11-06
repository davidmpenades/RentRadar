import json

import pytest
from django.conf import settings as django_settings
from django.test import RequestFactory
from rest_framework.request import Request

from apps.users.models import User
from apps.users.throttling import RegistrationThrottle, ip_bucket

PATH = "/register-like/"
SESSION_PATH = "/register-like-session/"
LIMIT = 10
HOUR = 3600
JSON = "application/json"
TOKEN = "a1B2c3D4" * 4
BODY = json.dumps({"email": "ana@correo.es", "password": "a-long-enough-one"})
IP = "203.0.113.7"


@pytest.fixture(autouse=True)
def test_urls(settings):
    settings.ROOT_URLCONF = "apps.users.tests.throttle_urls"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = Clock()
    # staticmethod: sin él Python pasaría la instancia como primer argumento
    monkeypatch.setattr(RegistrationThrottle, "timer", staticmethod(fake))
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


# ip_bucket


@pytest.mark.parametrize(
    ("address", "bucket"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("127.0.0.1", "127.0.0.1"),
        ("2001:db8:0:1::5", "2001:db8:0:1::/64"),
        ("2001:0DB8:0000:0001:0000:0000:0000:0005", "2001:db8:0:1::/64"),
        ("::1", "::/64"),
        ("fe80::1%eth0", "fe80::/64"),
        ("fe80::abcd%eth0", "fe80::/64"),
        ("fe80::1%1", "fe80::/64"),
        ("fe80::", "fe80::/64"),
        ("fe80::%eth0", "fe80::/64"),
        ("fe80::%eth1", "fe80::/64"),
        ("2001:db8:0:1::%x", "2001:db8:0:1::/64"),
    ],
)
def test_ip_bucket_groups_ipv6_by_64_and_keeps_ipv4(address, bucket):
    assert ip_bucket(address) == bucket


def test_two_addresses_of_the_same_64_share_a_bucket():
    assert ip_bucket("2001:db8:0:1::1") == ip_bucket("2001:db8:0:1:ffff:ffff::2")


def test_an_address_of_another_64_has_another_bucket():
    assert ip_bucket("2001:db8:0:1::1") != ip_bucket("2001:db8:0:2::1")
    assert ip_bucket("2001:db8:0:1::1") != ip_bucket("2001:db8:1:1::1")


def test_a_zone_is_dropped_and_the_address_groups_like_any_other():
    assert ip_bucket("fe80::1%eth0") == ip_bucket("fe80::2")
    assert ip_bucket("fe80::%eth0") == ip_bucket("fe80::%eth1") == ip_bucket("fe80::")


@pytest.mark.parametrize(
    ("mapped", "direct"),
    [
        ("::ffff:203.0.113.7", "203.0.113.7"),
        ("::FFFF:203.0.113.7", "203.0.113.7"),
        ("::ffff:cb00:7107", "203.0.113.7"),
        ("::ffff:203.0.113.7%eth0", "203.0.113.7"),
    ],
)
def test_a_mapped_ipv4_has_the_bucket_of_the_direct_ipv4(mapped, direct):
    assert ip_bucket(mapped) == ip_bucket(direct) == direct


def test_a_mapped_ipv4_is_not_grouped_by_its_64():
    assert ip_bucket("::ffff:203.0.113.7") != ip_bucket("::ffff:203.0.113.8")
    assert ip_bucket("::ffff:203.0.113.7") != "::/64"


WEIRD = [
    "",
    None,
    "unknown",
    "not an ip",
    " 203.0.113.7",
    "203.0.113.7 ",
    "203.0.113.7\n",
    "203.0.113.7/24",
    "203.0.113",
    "256.0.0.1",
    "010.0.0.1",
    "2001:db8::/64",
    "fe80::1%",
    "[2001:db8::1]",
    "\x00",
    "'; DROP TABLE users;--",
    "\u0661.\u0662.\u0663.\u0664",
    "a" * 10000,
    "1" * 10000,
    5,
    0,
    b"203.0.113.7",
    ["203.0.113.7"],
    {"a": 1},
    3.5,
]


@pytest.mark.parametrize("value", WEIRD, ids=[repr(v)[:30] for v in WEIRD])
def test_anything_that_is_not_an_address_goes_to_the_fixed_bucket(value):
    assert ip_bucket(value) == "unknown"


def test_a_very_long_zone_is_dropped_too():
    assert ip_bucket("fe80::1%" + "e" * 10000) == "fe80::/64"


def test_the_received_text_never_becomes_part_of_the_bucket():
    marker = "marker-9f3a"

    assert marker not in ip_bucket(marker)
    assert marker not in ip_bucket("fe80::1%" + marker)
    assert marker not in ip_bucket("fe80::%" + marker)


def test_the_cache_key_carries_the_scope_and_the_bucket_only():
    marker = "marker-9f3a"
    request = Request(RequestFactory().post(PATH, REMOTE_ADDR=marker))

    key = RegistrationThrottle().get_cache_key(request, None)

    assert key == "throttle_register_unknown"
    assert marker not in key


def test_the_cache_key_of_a_valid_address_uses_its_bucket():
    request = Request(RequestFactory().post(PATH, REMOTE_ADDR="2001:db8:0:1::9"))

    key = RegistrationThrottle().get_cache_key(request, None)

    assert key == "throttle_register_2001:db8:0:1::/64"


def test_the_limit_is_declared_on_the_class_and_not_read_from_settings():
    assert RegistrationThrottle.rate == "10/hour"
    assert RegistrationThrottle.scope == "register"
    assert RegistrationThrottle().num_requests == LIMIT
    assert RegistrationThrottle().duration == HOUR


# límite sobre una vista


def test_ten_requests_pass_and_the_eleventh_is_throttled(csrf_client, clock):
    fill_the_quota(csrf_client)

    response = post(csrf_client)

    retry_after = assert_throttled(response)
    assert retry_after == HOUR


def test_the_wait_shrinks_as_the_clock_advances(csrf_client, clock):
    fill_the_quota(csrf_client)
    clock.advance(600)

    assert assert_throttled(post(csrf_client)) == HOUR - 600


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
    clock.advance(100)
    first = assert_throttled(post(csrf_client))
    for _ in range(25):
        clock.advance(1)
        assert post(csrf_client).status_code == 429
    clock.advance(HOUR - 100 - 25)

    assert first == HOUR - 100
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


def test_a_mapped_ipv4_shares_the_quota_of_the_direct_ipv4(csrf_client, clock):
    fill_the_quota(csrf_client, ip="::ffff:203.0.113.7")

    assert_throttled(post(csrf_client, ip="203.0.113.7"))
    assert post(csrf_client, ip="203.0.113.8").status_code == 200


def test_ipv4_addresses_of_the_same_24_do_not_share_the_limit(csrf_client, clock):
    fill_the_quota(csrf_client, ip="203.0.113.7")

    assert post(csrf_client, ip="203.0.113.8").status_code == 200


def test_unusable_addresses_share_the_fixed_bucket_without_failing(csrf_client, clock):
    for index in range(LIMIT):
        assert post(csrf_client, ip=f"garbage-{index}").status_code == 200

    assert_throttled(post(csrf_client, ip="other garbage"))
    assert_throttled(post(csrf_client, ip=""))
    assert post(csrf_client, ip=IP).status_code == 200


def test_the_window_frees_up_as_the_clock_advances(csrf_client, clock):
    fill_the_quota(csrf_client)
    assert_throttled(post(csrf_client))

    clock.advance(HOUR - 1)
    assert_throttled(post(csrf_client))
    clock.advance(1)

    assert post(csrf_client).status_code == 200


def test_the_window_slides_instead_of_resetting(csrf_client, clock):
    for _ in range(5):
        assert post(csrf_client).status_code == 200
    clock.advance(HOUR // 2)
    for _ in range(5):
        assert post(csrf_client).status_code == 200
    assert_throttled(post(csrf_client))

    clock.advance(HOUR // 2)
    for _ in range(5):
        assert post(csrf_client).status_code == 200

    assert_throttled(post(csrf_client))


@pytest.mark.django_db
def test_a_logged_in_visitor_is_limited_too(csrf_client, clock):
    user = User.objects.create(email="ana@correo.es")
    csrf_client.force_login(user)
    fill_the_quota(csrf_client, path=SESSION_PATH)

    assert_throttled(post(csrf_client, path=SESSION_PATH))
