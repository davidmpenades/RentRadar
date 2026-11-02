import json
import logging
import re
import uuid
from unittest import mock

import pytest
from django.contrib.gis.geos import Point
from django.contrib.sessions.backends.db import SessionStore
from django.core.management import call_command
from django.db import connection
from django.test import RequestFactory
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle

from apps.assets.models import Asset
from apps.assets.tests.conftest import (
    SENTINEL_LATITUDE,
    SENTINEL_LONGITUDE,
    coordinate_forms,
)
from apps.assets.views import (
    PUBLIC_LIST_LIMIT,
    PUBLIC_LIST_MAX_AGE,
    PublicAssetListView,
    PublicListThrottle,
)
from apps.core.api import ERROR_CODES
from apps.users.models import User

pytestmark = pytest.mark.django_db

URL = "/api/v1/public/assets/"
VALENCIA_QUERY = {"south": "39.4", "west": "-0.4", "north": "39.5", "east": "-0.3"}
VALENCIA_PUBLIC = (39.4699, -0.3763)
# Desplazamiento fijo de la exacta respecto a la pública en los bienes de este módulo
EXACT_LATITUDE_OFFSET = 0.004
EXACT_LONGITUDE_OFFSET = 0.003
COORDINATE_TOLERANCE = 1e-9
REQUESTS_PER_MINUTE = 60
CLOCK_START = 1_000_000.0
ASSET_KEYS = {
    "public_id",
    "title",
    "category_slug",
    "category_name",
    "price",
    "currency",
    "price_unit",
    "privacy_radius",
    "latitude",
    "longitude",
}
ROOT_KEYS = {"results", "incomplete"}
PLANNED_CODES = {
    "invalid_parameters",
    "zone_inverted",
    "zone_too_large",
    "method_not_allowed",
    "throttled",
}
OTHER_IP = "10.1.1.1"


class FakeClock:
    def __init__(self):
        self.now = CLOCK_START

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    # staticmethod: una función normal recibiría la instancia como primer argumento
    monkeypatch.setattr(PublicListThrottle, "timer", staticmethod(fake))
    return fake


@pytest.fixture
def staff(db):
    return User.objects.create(email="staff@correo.es", is_staff=True)


@pytest.fixture
def build_asset(make_asset):
    # Recibe la ubicación pública; la exacta queda desplazada para poder distinguirlas
    def build(latitude=VALENCIA_PUBLIC[0], longitude=VALENCIA_PUBLIC[1], **overrides):
        fields = {
            "public_location": Point(longitude, latitude, srid=4326),
            "exact_location": Point(
                longitude + EXACT_LONGITUDE_OFFSET,
                latitude + EXACT_LATITUDE_OFFSET,
                srid=4326,
            ),
            "status": "active",
            **overrides,
        }
        return make_asset(**fields)

    return build


@pytest.fixture
def visible_asset(build_asset):
    def create(*args, **kwargs):
        asset = build_asset(*args, **kwargs)
        asset.save()
        return asset

    return create


def fetch(client, query=None, **extra):
    return client.get(URL, VALENCIA_QUERY if query is None else query, **extra)


def exhaust_limit(client, **extra):
    # Peticiones inválidas: cuestan una anotación y ninguna consulta
    for _ in range(REQUESTS_PER_MINUTE):
        assert client.get(URL, **extra).status_code == 400


def directives(response):
    return {
        part.strip().lower() for part in response["Cache-Control"].split(",") if part
    }


def vary_tokens(response):
    return {
        token.strip().lower()
        for token in response.headers.get("Vary", "").split(",")
        if token.strip()
    }


def access_control_headers(response):
    return [name for name in response.headers if name.lower().startswith("access-")]


def assert_no_cookies(response):
    assert "Set-Cookie" not in response.headers
    assert not response.cookies
    assert "cookie" not in vary_tokens(response)


def assert_error_format(response, sent_values=()):
    body = response.json()
    assert response["Content-Type"] == "application/json"
    assert isinstance(body["code"], str)
    assert set(body) <= {"code", "params", "retry_after"}
    assert ("params" in body) == (body["code"] == "invalid_parameters")
    assert ("retry_after" in body) == (body["code"] == "throttled")
    text = response.content.decode()
    for value in sent_values:
        assert value not in text
    return body


# --- Lo que ve cada visitante (la lista no distingue a nadie) -----------------


@pytest.mark.parametrize("viewer", ["anonymous", "owner", "staff"])
def test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets(
    client, owner, staff, visible_asset, viewer
):
    inside = visible_asset()
    visible_asset(title="Pausado", status="paused")
    visible_asset(41.0, -0.35, title="Fuera")
    inactive = User.objects.create(email="inactive@correo.es", is_active=False)
    visible_asset(title="Cuenta desactivada", owner=inactive)
    anonymous_body = fetch(client).json()

    if viewer != "anonymous":
        client.force_login({"owner": owner, "staff": staff}[viewer])
    response = fetch(client)

    assert response.status_code == 200
    assert response.json() == anonymous_body
    assert [item["public_id"] for item in anonymous_body["results"]] == [
        str(inside.public_id)
    ]


def test_a_paused_asset_never_appears_not_even_for_its_owner_with_a_session(
    client, owner, visible_asset
):
    visible_asset(status="paused")
    client.force_login(owner)

    assert fetch(client).json() == {"results": [], "incomplete": False}


def test_an_active_asset_of_a_deactivated_account_is_hidden(client, visible_asset):
    inactive = User.objects.create(email="inactive@correo.es", is_active=False)
    visible_asset(owner=inactive)

    assert fetch(client).json()["results"] == []


def test_assets_inside_the_zone_are_returned_and_outside_are_not(client, visible_asset):
    inside = visible_asset()
    visible_asset(40.4157, -3.7052)

    results = fetch(client).json()["results"]

    assert [item["public_id"] for item in results] == [str(inside.public_id)]


def test_coordinates_are_the_public_location_and_differ_from_the_exact_one(
    client, visible_asset
):
    asset = visible_asset()
    exact = asset.exact_location

    item = fetch(client).json()["results"][0]

    assert abs(item["latitude"] - VALENCIA_PUBLIC[0]) < COORDINATE_TOLERANCE
    assert abs(item["longitude"] - VALENCIA_PUBLIC[1]) < COORDINATE_TOLERANCE
    assert abs(item["latitude"] - exact.y) >= EXACT_LATITUDE_OFFSET - 1e-9
    assert abs(item["longitude"] - exact.x) >= EXACT_LONGITUDE_OFFSET - 1e-9


# --- Forma de la respuesta ----------------------------------------------------


def test_the_root_and_every_asset_have_exactly_the_planned_keys(client, visible_asset):
    visible_asset(title="Uno")
    visible_asset(title="Dos", privacy_radius=2000)

    body = fetch(client).json()

    assert set(body) == ROOT_KEYS
    assert len(body["results"]) == 2
    for item in body["results"]:
        assert set(item) == ASSET_KEYS


def test_the_body_never_contains_the_exact_location(client, visible_asset):
    asset = visible_asset()
    exact = asset.exact_location

    text = fetch(client).content.decode()

    for form in coordinate_forms(exact.x, exact.y, projected=False):
        assert form not in text


def test_asset_values_are_the_stored_ones(client, category, visible_asset):
    asset = visible_asset(title="Taladro", privacy_radius=2000)

    item = fetch(client).json()["results"][0]

    assert item["title"] == "Taladro"
    assert item["category_slug"] == category.slug
    assert item["category_name"] == category.name
    assert item["currency"] == "EUR"
    assert item["price_unit"] == "day"
    assert item["privacy_radius"] == 2000
    assert item["public_id"] == str(asset.public_id)


def test_the_price_is_text_with_two_decimals(client, visible_asset):
    visible_asset(price="12.5")

    price = fetch(client).json()["results"][0]["price"]

    assert price == "12.50"
    assert isinstance(price, str)


def test_the_public_id_is_a_random_uuid_distinct_from_the_primary_key(
    client, visible_asset
):
    asset = visible_asset()

    public_id = fetch(client).json()["results"][0]["public_id"]

    assert uuid.UUID(public_id).version == 4
    assert public_id != str(asset.pk)
    assert asset.pk != asset.public_id


# --- Zona inválida ------------------------------------------------------------


def query_without(name):
    return {key: value for key, value in VALENCIA_QUERY.items() if key != name}


INVALID_PARAMETER_CASES = [
    pytest.param(query_without("south"), {"south": "required"}, id="missing_south"),
    pytest.param(
        {**VALENCIA_QUERY, "west": ""}, {"west": "not_a_number"}, id="empty_west"
    ),
    pytest.param(
        {**VALENCIA_QUERY, "north": "9" * 33}, {"north": "too_long"}, id="too_long"
    ),
    pytest.param(
        {**VALENCIA_QUERY, "east": "1e1"}, {"east": "not_a_number"}, id="exponent"
    ),
    pytest.param(
        {**VALENCIA_QUERY, "north": "95"}, {"north": "out_of_range"}, id="north_range"
    ),
    pytest.param(
        {**VALENCIA_QUERY, "south": "x", "east": "999"},
        {"south": "not_a_number", "east": "out_of_range"},
        id="one_code_per_failing_bound",
    ),
]


@pytest.mark.parametrize(("query", "params"), INVALID_PARAMETER_CASES)
def test_an_invalid_bound_returns_one_code_per_failing_parameter(client, query, params):
    response = fetch(client, query)

    assert response.status_code == 400
    assert response.json() == {"code": "invalid_parameters", "params": params}


def test_a_repeated_bound_is_rejected(client):
    query_string = "south=39.4&west=-0.4&north=39.5&east=-0.3&east=-0.2"

    response = client.get(f"{URL}?{query_string}")

    assert response.status_code == 400
    assert response.json() == {
        "code": "invalid_parameters",
        "params": {"east": "repeated"},
    }


ZONE_CASES = [
    pytest.param(
        {"south": "39.5", "west": "-0.4", "north": "39.4", "east": "-0.3"},
        "zone_inverted",
        id="inverted",
    ),
    pytest.param(
        {"south": "39", "west": "-1", "north": "42.1", "east": "1"},
        "zone_too_large",
        id="too_large",
    ),
]


@pytest.mark.parametrize(("query", "code"), ZONE_CASES)
def test_a_wrong_zone_returns_only_its_own_code(client, query, code):
    response = fetch(client, query)

    assert response.status_code == 400
    assert response.json() == {"code": code}


def test_input_errors_are_not_stored_and_do_not_echo_the_values_or_log_them(
    client, caplog
):
    sent = {
        "south": "zzqq111",
        "west": "39.512345",
        "north": "39.598765",
        "east": "99999999",
    }
    caplog.set_level(logging.DEBUG)

    response = fetch(client, sent)

    assert response.status_code == 400
    assert "no-store" in directives(response)
    assert_error_format(response, sent.values())
    for value in sent.values():
        assert value not in caplog.text


def test_unknown_parameters_are_ignored(client, visible_asset):
    visible_asset()
    expected = fetch(client).json()

    for extra in ({"format": "xml"}, {"category": "pool"}, {"q": "taladro"}):
        response = fetch(client, {**VALENCIA_QUERY, **extra})

        assert response.status_code == 200
        assert response.json() == expected


# --- Tope de resultados -------------------------------------------------------


def test_201_visible_assets_return_200_and_are_incomplete(client, build_asset):
    Asset.objects.bulk_create([build_asset() for _ in range(201)])

    body = fetch(client).json()

    assert len(body["results"]) == 200
    assert body["incomplete"] is True


def test_exactly_200_visible_assets_are_complete(client, build_asset):
    Asset.objects.bulk_create([build_asset() for _ in range(200)])

    body = fetch(client).json()

    assert len(body["results"]) == 200
    assert body["incomplete"] is False


def test_the_response_has_no_total_or_count_anywhere(client, build_asset):
    Asset.objects.bulk_create([build_asset() for _ in range(201)])

    body = fetch(client).json()

    names = set(body) | {key for item in body["results"] for key in item}
    assert names == ROOT_KEYS | ASSET_KEYS
    assert not any(re.search(r"total|count|num", name) for name in names)


# --- Límite de peticiones -----------------------------------------------------


def test_the_throttle_is_an_anonymous_rate_throttle_with_its_own_scope_and_rate():
    assert issubclass(PublicListThrottle, AnonRateThrottle)
    assert PublicListThrottle.rate == "60/min"
    assert PublicListThrottle.scope == "public_assets"


def test_60_unsupported_methods_are_answered_405_and_the_next_request_is_429(
    client, clock
):
    for _ in range(REQUESTS_PER_MINUTE):
        assert client.post(URL).status_code == 405

    response = client.post(URL)

    assert response.status_code == 429
    assert response.json()["code"] == "throttled"


def test_60_invalid_requests_are_answered_400_and_the_next_request_is_429(
    client, clock
):
    exhaust_limit(client)

    assert client.get(URL).status_code == 429


def test_valid_requests_count_too(client, clock, visible_asset):
    visible_asset()
    for _ in range(REQUESTS_PER_MINUTE):
        assert fetch(client).status_code == 200

    assert fetch(client).status_code == 429


@pytest.mark.parametrize("method", ["get", "post", "options", "head"])
def test_with_the_limit_exceeded_every_method_is_429_without_validating_or_querying(
    client, clock, django_assert_num_queries, method
):
    exhaust_limit(client)

    with django_assert_num_queries(0):
        response = getattr(client, method)(URL, VALENCIA_QUERY)

    assert response.status_code == 429


def test_with_the_limit_exceeded_an_invalid_zone_is_still_429(client, clock):
    exhaust_limit(client)

    response = client.get(URL, {"south": "zzqq"})

    assert response.status_code == 429
    assert response.json()["code"] == "throttled"


def test_throttled_responses_do_not_count_so_insisting_does_not_extend_the_wait(
    client, clock
):
    exhaust_limit(client)
    first = fetch(client).json()["retry_after"]

    for _ in range(5):
        assert fetch(client).json()["retry_after"] == first

    clock.advance(10)
    assert fetch(client).json()["retry_after"] == first - 10


def test_a_burst_of_429s_does_not_keep_the_limit_closed_after_the_window(client, clock):
    exhaust_limit(client)
    clock.advance(30)
    for _ in range(REQUESTS_PER_MINUTE):
        assert fetch(client).status_code == 429

    clock.advance(30.5)

    assert fetch(client).status_code == 200


def test_advancing_the_clock_enough_releases_the_limit(client, clock):
    exhaust_limit(client)
    assert fetch(client).status_code == 429

    clock.advance(61)

    assert fetch(client).status_code == 200


def test_different_forwarded_for_headers_count_for_the_same_address(client, clock):
    for index in range(REQUESTS_PER_MINUTE):
        response = client.get(URL, HTTP_X_FORWARDED_FOR=f"203.0.113.{index}")
        assert response.status_code == 400

    response = client.get(URL, HTTP_X_FORWARDED_FOR="198.51.100.77")

    assert response.status_code == 429


def test_another_remote_address_has_its_own_counter(client, clock):
    exhaust_limit(client)

    assert fetch(client, REMOTE_ADDR=OTHER_IP).status_code == 200
    assert fetch(client).status_code == 429


def test_the_limit_of_one_address_does_not_include_requests_of_another(client, clock):
    exhaust_limit(client, REMOTE_ADDR=OTHER_IP)

    assert fetch(client).status_code == 200


def test_a_logged_in_visitor_counts_like_an_anonymous_one(client, clock, owner):
    exhaust_limit(client)
    client.force_login(owner)

    response = fetch(client)

    assert response.status_code == 429


def test_retry_after_is_an_integer_of_at_least_one_equal_to_the_body(client, clock):
    exhaust_limit(client)
    clock.advance(59.2)

    response = fetch(client)

    assert re.fullmatch(r"[1-9][0-9]*", response["Retry-After"])
    assert int(response["Retry-After"]) == response.json()["retry_after"]
    assert response.json()["retry_after"] >= 1


def test_the_throttled_response_is_not_stored(client, clock):
    exhaust_limit(client)

    assert "no-store" in directives(fetch(client))


# --- Permisos -----------------------------------------------------------------


def test_the_view_declares_its_own_authentication_permissions_and_methods():
    assert PublicAssetListView.authentication_classes == []
    assert PublicAssetListView.permission_classes == [AllowAny]
    assert PublicAssetListView.throttle_classes == [PublicListThrottle]
    assert PublicAssetListView.http_method_names == ["get", "head"]


@pytest.mark.parametrize("login", [False, True], ids=["anonymous", "logged_in"])
@pytest.mark.parametrize("method", ["get", "head"])
def test_get_and_head_are_allowed(client, owner, login, method):
    if login:
        client.force_login(owner)

    response = getattr(client, method)(URL, VALENCIA_QUERY)

    assert response.status_code == 200


@pytest.mark.parametrize("login", [False, True], ids=["anonymous", "logged_in"])
@pytest.mark.parametrize(
    "method", ["options", "post", "put", "patch", "delete", "trace"]
)
def test_every_other_method_is_405_with_the_single_format(client, owner, login, method):
    if login:
        client.force_login(owner)

    response = getattr(client, method)(URL, VALENCIA_QUERY)

    assert response.status_code == 405
    assert response.json() == {"code": "method_not_allowed"}
    assert "no-store" in directives(response)
    assert response["Allow"] == "GET, HEAD"


# --- Caché --------------------------------------------------------------------


def test_the_success_response_is_public_for_60_seconds(client, visible_asset):
    visible_asset()

    response = fetch(client)

    assert directives(response) == {"public", f"max-age={PUBLIC_LIST_MAX_AGE}"}


def test_the_max_age_and_the_limit_are_the_planned_ones():
    assert PUBLIC_LIST_MAX_AGE == 60
    assert PUBLIC_LIST_LIMIT == 200


def test_error_responses_are_never_cached(client, clock):
    invalid = client.get(URL)
    not_allowed = client.post(URL)
    exhaust_limit(client, REMOTE_ADDR=OTHER_IP)
    throttled = fetch(client, REMOTE_ADDR=OTHER_IP)

    for response, status in ((invalid, 400), (not_allowed, 405), (throttled, 429)):
        assert response.status_code == status
        assert "no-store" in directives(response)
        assert "public" not in directives(response)


# --- Respuesta idéntica para cualquier visitante ------------------------------


def assert_same_public_answer(baseline, response):
    assert response.status_code == 200
    assert response.content == baseline.content
    assert response["Content-Type"] == "application/json"
    assert response["Cache-Control"] == baseline["Cache-Control"]
    assert response["Vary"] == "Accept-Encoding"
    assert_no_cookies(response)
    assert access_control_headers(response) == []


IDENTICAL_VARIANTS = [
    pytest.param({}, {"HTTP_AUTHORIZATION": "Bearer token"}, id="authorization"),
    pytest.param({}, {"HTTP_ORIGIN": "https://other.example"}, id="origin"),
    pytest.param({}, {"HTTP_ACCEPT": "application/xml"}, id="accept_xml"),
    pytest.param({"format": "xml"}, {}, id="format_query"),
    pytest.param({}, {"HTTP_X_FORWARDED_FOR": "203.0.113.9"}, id="forwarded_for"),
]


@pytest.mark.parametrize(("query_extra", "headers"), IDENTICAL_VARIANTS)
def test_the_answer_does_not_depend_on_the_visitor_headers(
    client, visible_asset, query_extra, headers
):
    visible_asset()
    baseline = fetch(client)

    response = fetch(client, {**VALENCIA_QUERY, **query_extra}, **headers)

    assert_same_public_answer(baseline, response)


def test_the_session_is_never_read_and_the_answer_is_the_same(
    client, owner, visible_asset
):
    visible_asset()
    baseline = fetch(client)
    client.force_login(owner)

    with mock.patch.object(
        SessionStore, "load", side_effect=AssertionError("sesión leída")
    ) as load:
        response = fetch(client)

    assert_same_public_answer(baseline, response)
    assert load.call_count == 0


MALFORMED_COOKIES = [
    pytest.param({"csrftoken": "x"}, id="csrftoken"),
    pytest.param({"sessionid": "short"}, id="sessionid"),
    pytest.param({"csrftoken": "x", "sessionid": "short"}, id="both"),
]


def set_cookies(client, cookies):
    for name, value in cookies.items():
        client.cookies[name] = value


@pytest.mark.parametrize("cookies", MALFORMED_COOKIES)
def test_malformed_cookies_do_not_make_the_success_response_set_cookies(
    client, visible_asset, cookies
):
    visible_asset()
    baseline = fetch(client)
    set_cookies(client, cookies)

    response = fetch(client)

    assert_same_public_answer(baseline, response)


def test_head_has_the_same_headers_as_get_and_no_body(client, visible_asset):
    visible_asset()
    get = fetch(client)

    head = client.head(URL, VALENCIA_QUERY)

    assert head.status_code == 200
    assert head.content == b""
    for header in ("Cache-Control", "Vary", "Allow", "Content-Type"):
        assert head[header] == get[header]
    assert_no_cookies(head)


# --- Errores sin cookies ------------------------------------------------------

ERROR_SENDERS = {
    400: lambda client: client.get(URL),
    405: lambda client: client.post(URL),
    429: lambda client: fetch(client),
}


@pytest.mark.parametrize("cookies", MALFORMED_COOKIES)
@pytest.mark.parametrize("status", [400, 405, 429])
def test_error_responses_of_the_view_leave_without_cookies(
    client, clock, status, cookies
):
    if status == 429:
        exhaust_limit(client)
    set_cookies(client, cookies)

    response = ERROR_SENDERS[status](client)

    assert response.status_code == status
    assert_no_cookies(response)


def test_an_unmarked_response_for_the_same_cookie_does_set_cookies(client):
    set_cookies(client, {"csrftoken": "x"})

    response = client.get("/api/v1/public/not-the-list/")

    assert response.status_code == 404
    assert "csrftoken" in response.cookies


def call_view(method="get", query=None):
    # Sin middleware: lo que sale de la vista por sí misma
    factory = RequestFactory()
    request = getattr(factory, method)(URL, VALENCIA_QUERY if query is None else query)
    return PublicAssetListView.as_view()(request)


def test_the_view_itself_marks_every_response_and_declares_only_its_own_vary(clock):
    responses = [
        call_view(),
        call_view(query={}),
        call_view("post"),
    ]
    for _ in range(REQUESTS_PER_MINUTE):
        call_view(query={})
    responses.append(call_view())

    assert [response.status_code for response in responses] == [200, 400, 405, 429]
    for response in responses:
        assert response.cookieless is True
        assert access_control_headers(response) == []
        assert not response.cookies
    assert responses[0]["Vary"] == "Accept-Encoding"
    assert "Vary" not in responses[1]


# --- Formato único de los errores ---------------------------------------------


def request_invalid_parameters(client):
    return client.get(URL, {**VALENCIA_QUERY, "south": "zzqq"})


def request_zone_inverted(client):
    return fetch(client, ZONE_CASES[0].values[0])


def request_zone_too_large(client):
    return fetch(client, ZONE_CASES[1].values[0])


def request_method_not_allowed(client):
    return client.post(URL)


def request_throttled(client):
    exhaust_limit(client, REMOTE_ADDR=OTHER_IP)
    return fetch(client, REMOTE_ADDR=OTHER_IP)


ERROR_REQUESTS = [
    pytest.param(request_invalid_parameters, 400, "invalid_parameters", id="invalid"),
    pytest.param(request_zone_inverted, 400, "zone_inverted", id="inverted"),
    pytest.param(request_zone_too_large, 400, "zone_too_large", id="too_large"),
    pytest.param(request_method_not_allowed, 405, "method_not_allowed", id="method"),
    pytest.param(request_throttled, 429, "throttled", id="throttled"),
]


@pytest.mark.parametrize(("send", "status", "code"), ERROR_REQUESTS)
def test_every_error_of_the_list_has_the_single_format(
    client, clock, send, status, code
):
    response = send(client)

    assert response.status_code == status
    body = assert_error_format(response, ["zzqq", "39.5", "42.1"])
    assert body["code"] == code
    assert "detail" not in body
    assert "no-store" in directives(response)


def test_the_codes_returned_by_all_the_paths_are_exactly_the_planned_ones(
    client, clock
):
    codes = {request.values[0](client).json()["code"] for request in ERROR_REQUESTS}

    assert codes == PLANNED_CODES
    assert codes <= ERROR_CODES


# --- Logs ---------------------------------------------------------------------


def test_no_form_of_the_exact_coordinates_reaches_the_logs(client, build_asset, caplog):
    build_asset(
        40.4157,
        -3.7052,
        exact_location=Point(SENTINEL_LONGITUDE, SENTINEL_LATITUDE, srid=4326),
    ).save()
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="django.db.backends")
    query = {"south": "40.3", "west": "-3.8", "north": "40.5", "east": "-3.6"}

    connection.force_debug_cursor = True
    try:
        response = fetch(client, query)
    finally:
        connection.force_debug_cursor = False

    assert len(response.json()["results"]) == 1
    assert "SELECT" in caplog.text
    for form in coordinate_forms(SENTINEL_LONGITUDE, SENTINEL_LATITUDE):
        assert form not in caplog.text


# --- Descripción OpenAPI ------------------------------------------------------


def resolve(spec, node):
    while "$ref" in node:
        target = spec
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def test_the_openapi_description_is_valid_and_documents_the_list(tmp_path):
    destination = tmp_path / "openapi.json"

    call_command(
        "spectacular",
        "--validate",
        "--fail-on-warn",
        "--format",
        "openapi-json",
        "--lang",
        "en",
        "--file",
        str(destination),
    )

    spec = json.loads(destination.read_text())
    path = spec["paths"][URL]
    assert set(path) == {"get"}
    operation = path["get"]
    assert operation["operationId"] == "listPublicAssets"
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) == {"south", "west", "north", "east"}
    for parameter in parameters.values():
        assert parameter["in"] == "query"
        assert parameter["required"] is True
    assert set(operation["responses"]) == {"200", "400", "405", "429"}
    schema = resolve(
        spec, operation["responses"]["200"]["content"]["application/json"]["schema"]
    )
    assert set(schema["properties"]) == ROOT_KEYS
    asset_schema = resolve(spec, schema["properties"]["results"]["items"])
    assert set(asset_schema["properties"]) == ASSET_KEYS
