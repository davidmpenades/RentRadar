from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from django.contrib.gis.geos import Point
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.assets.location import PRIVACY_RADII, ApproximationError, approximate_location
from apps.assets.models import Asset
from apps.assets.services import ERROR_CODES, create_asset, update_asset
from apps.assets.tests.conftest import NOW
from apps.categories.models import Category
from apps.core.errors import DomainValidationError

LATER = NOW + timedelta(hours=1)
MOVED = {"latitude": 40.5, "longitude": -3.6}
LOCATION_LOCKED = {"location": ["location_locked"]}
RADIUS_LOCKED = {"privacy_radius": ["privacy_radius_locked"]}
UNCHANGED_ARGUMENTS = {
    "nothing": {},
    "same_price_with_a_trailing_zero": {"price": "12.340"},
    "same_title_with_spaces": {"title": "  Taladro  "},
    "same_description": {"description": "Taladro de percusion en buen estado"},
    "same_currency": {"currency": "EUR"},
    "same_price_unit": {"price_unit": "day"},
    "same_radius": {"privacy_radius": 1000},
    "same_status": {"status": "paused"},
    "same_coordinates": {"latitude": 40.4168, "longitude": -3.7038},
}
INVALID_FIELDS = {
    "category_is_text": ({"category_id": "5"}, {"category": ["category_invalid"]}),
    "title_too_short": ({"title": "ab"}, {"title": ["title_too_short"]}),
    "price_out_of_range": ({"price": "0"}, {"price": ["price_out_of_range"]}),
    "currency": ({"currency": "USD"}, {"currency": ["currency_invalid"]}),
    "price_unit": ({"price_unit": "night"}, {"price_unit": ["price_unit_invalid"]}),
    "privacy_radius": (
        {"privacy_radius": 1500},
        {"privacy_radius": ["privacy_radius_invalid"]},
    ),
    "swapped_coordinates": (
        {"latitude": -3.7038, "longitude": 40.4168},
        {"location": ["location_outside_bounds"]},
    ),
}
REQUIRED_ARGUMENTS = [
    ("category_id", "category"),
    ("title", "title"),
    ("description", "description"),
    ("price", "price"),
    ("price_unit", "price_unit"),
]
DEFAULTLESS_ARGUMENTS = [
    ("currency", "currency_invalid"),
    ("privacy_radius", "privacy_radius_invalid"),
    ("status", "status_invalid"),
]
INVALID_STATUSES = {"deleted": "deleted", "capitalised": "Active", "none": None}
SINGLE_COORDINATES = {
    "only_latitude": {"latitude": 40.5},
    "only_longitude": {"longitude": -3.6},
    "latitude_and_none": {"latitude": 40.5, "longitude": None},
    "none_and_longitude": {"latitude": None, "longitude": -3.6},
}
FORBIDDEN_ARGUMENTS = {
    "owner_id": 1,
    "public_location": Point(-3.7038123, 40.4168456, srid=4326),
    "exact_location": Point(-3.7038123, 40.4168456, srid=4326),
    "id": 1,
    "pk": 1,
    "created_at": datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
    "updated_at": datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
    "owner": object(),
    "category": object(),
}
INVALID_NOW = {
    "naive": datetime(2026, 10, 27, 12, 0),
    "none": None,
    "text": "2026-10-27T12:00:00+00:00",
    "number": 5,
}
INVALID_ASSET_IDS = {"bool": True, "text": "5", "zero": 0}
REJECTED_BY_THE_LOCK = {
    "active_and_moved": ("active", MOVED, LOCATION_LOCKED),
    "active_and_other_radius": ("active", {"privacy_radius": 2000}, RADIUS_LOCKED),
    "active_moved_and_other_radius": (
        "active",
        {**MOVED, "privacy_radius": 2000},
        {**LOCATION_LOCKED, **RADIUS_LOCKED},
    ),
    "paused_and_moved_in_one_call": (
        "active",
        {"status": "paused", **MOVED},
        LOCATION_LOCKED,
    ),
    "paused_and_other_radius_in_one_call": (
        "active",
        {"status": "paused", "privacy_radius": 2000},
        RADIUS_LOCKED,
    ),
    "activated_and_moved": ("paused", {"status": "active", **MOVED}, LOCATION_LOCKED),
    "activated_and_other_radius": (
        "paused",
        {"status": "active", "privacy_radius": 2000},
        RADIUS_LOCKED,
    ),
    "activated_moved_and_other_radius": (
        "paused",
        {"status": "active", **MOVED, "privacy_radius": 2000},
        {**LOCATION_LOCKED, **RADIUS_LOCKED},
    ),
    "unknown_category_and_active_moved": (
        "active",
        {"category_id": 999_999_999, **MOVED},
        {"category": ["category_not_found"], **LOCATION_LOCKED},
    ),
}
COLUMNS_OF_THE_UPDATE = {
    "title": ({"title": "Martillo"}, {"title", "updated_at"}),
    "price": ({"price": "20"}, {"price", "updated_at"}),
    "location": (
        MOVED,
        {"exact_location", "public_location", "updated_at"},
    ),
    "radius": (
        {"privacy_radius": 2000},
        {"privacy_radius", "public_location", "updated_at"},
    ),
    "status": ({"status": "active"}, {"status", "updated_at"}),
    "category": ({"category_id": "kayak"}, {"category_id", "updated_at"}),
}


def modify(asset, **changes):
    return update_asset(now=LATER, asset_id=asset.pk, **changes)


def modification_errors(asset, **changes):
    with pytest.raises(DomainValidationError) as caught:
        modify(asset, **changes)
    errors = caught.value.message_dict
    assert {code for codes in errors.values() for code in codes} <= ERROR_CODES
    return errors


def activate(asset):
    Asset.objects.filter(pk=asset.pk).update(status="active")


def row_of(asset):
    return Asset.objects.filter(pk=asset.pk).values().get()


def updates_of(captured):
    return [
        query["sql"]
        for query in captured.captured_queries
        if query["sql"].lstrip().upper().startswith("UPDATE")
    ]


def columns_of(update):
    assignments = update.partition(" SET ")[2].partition(" WHERE ")[0]
    return {part.split(" = ")[0].strip('"') for part in assignments.split(", ")}


def test_a_change_sets_updated_at_in_utc_and_keeps_created_at(stored_asset):
    local = LATER.astimezone(timezone(timedelta(hours=2)))

    returned = update_asset(now=local, asset_id=stored_asset.pk, title="Martillo")

    for saved in (returned, Asset.objects.get(pk=stored_asset.pk)):
        assert saved.title == "Martillo"
        assert saved.updated_at == LATER
        assert saved.updated_at.utcoffset() == timedelta(0)
        assert saved.created_at == NOW


@pytest.mark.parametrize(
    "arguments", UNCHANGED_ARGUMENTS.values(), ids=UNCHANGED_ARGUMENTS
)
def test_a_modification_without_changes_writes_nothing(stored_asset, arguments):
    before = row_of(stored_asset)

    with CaptureQueriesContext(connection) as captured:
        returned = modify(stored_asset, **arguments)

    assert updates_of(captured) == []
    assert row_of(stored_asset) == before
    assert returned.updated_at == NOW


def test_activating_an_active_asset_and_pausing_a_paused_one_writes_nothing(
    stored_asset,
):
    paused_before = row_of(stored_asset)
    with CaptureQueriesContext(connection) as paused_captured:
        modify(stored_asset, status="paused")
    activate(stored_asset)
    active_before = row_of(stored_asset)

    with CaptureQueriesContext(connection) as active_captured:
        modify(stored_asset, status="active")

    assert updates_of(paused_captured) == []
    assert updates_of(active_captured) == []
    assert paused_before["status"] == "paused"
    assert row_of(stored_asset) == active_before


def test_a_title_change_keeps_the_rest_of_an_active_asset(creation_arguments):
    asset = create_asset(**{**creation_arguments, "privacy_radius": 2000})
    activate(asset)
    before = row_of(asset)

    modify(asset, title="Martillo")

    assert row_of(asset) == {**before, "title": "Martillo", "updated_at": LATER}
    assert (before["privacy_radius"], before["status"]) == (2000, "active")


def test_the_changed_values_are_stored_normalised(stored_asset):
    modify(
        stored_asset,
        title="  Martillo  ",
        description="Cafe" + chr(0x301) + " para el martillo de goma",
        price="20.500",
        price_unit="week",
    )

    stored = Asset.objects.get(pk=stored_asset.pk)
    assert stored.title == "Martillo"
    assert stored.description == "Caf" + chr(0xE9) + " para el martillo de goma"
    assert stored.price == Decimal("20.50")
    assert stored.price_unit == "week"


@pytest.mark.parametrize(
    ("overrides", "expected"), INVALID_FIELDS.values(), ids=INVALID_FIELDS
)
def test_an_invalid_field_gets_its_code_without_touching_the_database(
    stored_asset, django_assert_num_queries, overrides, expected
):
    before = row_of(stored_asset)

    with django_assert_num_queries(0):
        errors = modification_errors(stored_asset, **overrides)

    assert errors == expected
    assert row_of(stored_asset) == before


@pytest.mark.parametrize(("argument", "field"), REQUIRED_ARGUMENTS)
def test_none_in_a_required_field_gets_its_required_code(stored_asset, argument, field):
    errors = modification_errors(stored_asset, **{argument: None})

    assert errors == {field: [f"{field}_required"]}


@pytest.mark.parametrize(("argument", "code"), DEFAULTLESS_ARGUMENTS)
def test_none_in_currency_radius_or_status_is_invalid_not_required(
    stored_asset, argument, code
):
    errors = modification_errors(stored_asset, **{argument: None})

    assert errors == {argument: [code]}


@pytest.mark.parametrize(
    "coordinates", SINGLE_COORDINATES.values(), ids=SINGLE_COORDINATES
)
def test_a_single_coordinate_gets_the_location_required_code(stored_asset, coordinates):
    before = row_of(stored_asset)

    errors = modification_errors(stored_asset, **coordinates)

    assert errors == {"location": ["location_required"]}
    assert row_of(stored_asset) == before


def test_several_invalid_fields_are_reported_together(stored_asset):
    errors = modification_errors(
        stored_asset,
        title="ab",
        price="0",
        status="active",
        latitude=40.5,
        category_id=None,
    )

    assert errors == {
        "category": ["category_required"],
        "title": ["title_too_short"],
        "price": ["price_out_of_range"],
        "location": ["location_required"],
    }


@pytest.mark.parametrize("status", INVALID_STATUSES.values(), ids=INVALID_STATUSES)
def test_a_status_outside_active_and_paused_is_invalid(stored_asset, status):
    errors = modification_errors(stored_asset, status=status)

    assert errors == {"status": ["status_invalid"]}


def test_an_asset_can_be_activated_and_paused(stored_asset):
    modify(stored_asset, status="active")
    assert Asset.objects.get(pk=stored_asset.pk).status == "active"

    modify(stored_asset, status="paused")
    assert Asset.objects.get(pk=stored_asset.pk).status == "paused"


def test_the_owner_cannot_be_changed(stored_asset):
    owner_id = stored_asset.owner_id

    with pytest.raises(TypeError) as caught:
        modify(stored_asset, owner_id=owner_id + 1)

    assert "owner_id" in str(caught.value)
    assert Asset.objects.get(pk=stored_asset.pk).owner_id == owner_id


def test_the_category_can_be_changed_to_another_one(stored_asset):
    kayak = Category.objects.get(slug="kayak")

    modify(stored_asset, category_id=kayak.pk)

    assert Asset.objects.get(pk=stored_asset.pk).category_id == kayak.pk


def test_an_unknown_category_is_reported_and_nothing_changes(stored_asset):
    before = row_of(stored_asset)

    errors = modification_errors(
        stored_asset, category_id=999_999_999, title="Martillo"
    )

    assert errors == {"category": ["category_not_found"]}
    assert row_of(stored_asset) == before


@pytest.mark.parametrize(
    ("name", "value"), FORBIDDEN_ARGUMENTS.items(), ids=FORBIDDEN_ARGUMENTS
)
def test_an_argument_outside_the_whitelist_is_a_programming_error(
    stored_asset, name, value
):
    before = row_of(stored_asset)

    with pytest.raises(TypeError) as caught:
        modify(stored_asset, **{name: value})

    assert name in str(caught.value)
    assert "3.7038123" not in str(caught.value)
    assert "40.4168456" not in str(caught.value)
    assert row_of(stored_asset) == before


def test_the_arguments_are_keyword_only(stored_asset):
    with pytest.raises(TypeError):
        update_asset(LATER, stored_asset.pk)


def test_now_and_the_asset_are_required(stored_asset):
    with pytest.raises(TypeError):
        update_asset(asset_id=stored_asset.pk)
    with pytest.raises(TypeError):
        update_asset(now=LATER)


@pytest.mark.parametrize("now", INVALID_NOW.values(), ids=INVALID_NOW)
def test_a_now_without_a_time_zone_is_a_programming_error(
    stored_asset, django_assert_num_queries, now
):
    with django_assert_num_queries(0), pytest.raises(ValueError) as caught:
        update_asset(now=now, asset_id=stored_asset.pk, title="Martillo")

    assert str(caught.value) == "now_not_aware"


def test_an_unknown_asset_is_not_found(stored_asset):
    with pytest.raises(DomainValidationError) as caught:
        update_asset(now=LATER, asset_id=stored_asset.pk + 999_999, title="Martillo")

    assert caught.value.message_dict == {"asset": ["asset_not_found"]}
    assert caught.value.__context__ is None


@pytest.mark.parametrize("asset_id", INVALID_ASSET_IDS.values(), ids=INVALID_ASSET_IDS)
def test_an_invalid_asset_id_is_not_found_without_asking_the_database(
    db, django_assert_num_queries, asset_id
):
    with django_assert_num_queries(0), pytest.raises(DomainValidationError) as caught:
        update_asset(now=LATER, asset_id=asset_id, title="Martillo")

    assert caught.value.message_dict == {"asset": ["asset_not_found"]}


def public_of(asset):
    stored = Asset.objects.get(pk=asset.pk)
    return stored.public_location.coords, stored


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_a_new_radius_derives_the_public_location_from_the_stored_exact_one(
    stored_asset, radius
):
    modify(stored_asset, privacy_radius=radius)

    coords, stored = public_of(stored_asset)
    latitude, longitude = approximate_location(40.4168, -3.7038, radius)
    assert stored.privacy_radius == radius
    assert coords == (longitude, latitude)


def test_moving_the_exact_location_derives_a_new_public_one(stored_asset):
    before, _ = public_of(stored_asset)

    modify(stored_asset, **MOVED)

    coords, stored = public_of(stored_asset)
    latitude, longitude = approximate_location(40.5, -3.6, 1000)
    assert stored.exact_location.coords == (-3.6, 40.5)
    assert coords == (longitude, latitude)
    assert coords != before


def test_after_creations_and_modifications_every_public_location_is_derived(
    stored_asset,
):
    steps = [
        {"latitude": 41.38, "longitude": 2.17},
        {"privacy_radius": 500},
        {"title": "Martillo"},
        {"latitude": 28.1235, "longitude": -15.4363, "privacy_radius": 2000},
        {"status": "active"},
        {"title": "Martillo grande"},
    ]

    for step in steps:
        modify(stored_asset, **step)
        coords, stored = public_of(stored_asset)
        latitude, longitude = approximate_location(
            stored.exact_location.y, stored.exact_location.x, stored.privacy_radius
        )
        assert coords == (longitude, latitude)


def test_moving_inside_the_same_cell_leaves_the_public_location_alone(stored_asset):
    before, _ = public_of(stored_asset)
    centre_longitude, centre_latitude = before

    modify(stored_asset, latitude=centre_latitude, longitude=centre_longitude)

    coords, stored = public_of(stored_asset)
    assert stored.exact_location.coords == before
    assert coords == before


def test_changing_something_else_does_not_derive_the_public_location(
    monkeypatch, stored_asset
):
    calls = []

    def spy(latitude, longitude, radius):
        calls.append(radius)
        return approximate_location(latitude, longitude, radius)

    monkeypatch.setattr("apps.assets.services.approximate_location", spy)
    before, _ = public_of(stored_asset)

    modify(stored_asset, title="Martillo", price="20", status="active")

    assert calls == []
    assert public_of(stored_asset)[0] == before


def test_the_spy_sees_the_derivation_when_the_radius_changes(monkeypatch, stored_asset):
    calls = []

    def spy(latitude, longitude, radius):
        calls.append(radius)
        return approximate_location(latitude, longitude, radius)

    monkeypatch.setattr("apps.assets.services.approximate_location", spy)

    modify(stored_asset, privacy_radius=2000)

    assert calls == [2000]


@pytest.mark.parametrize(
    ("status", "overrides", "expected"),
    REJECTED_BY_THE_LOCK.values(),
    ids=REJECTED_BY_THE_LOCK,
)
def test_an_active_or_activated_asset_cannot_change_location_or_radius(
    stored_asset, status, overrides, expected
):
    if status == "active":
        activate(stored_asset)
    before = row_of(stored_asset)

    errors = modification_errors(stored_asset, **overrides)

    assert errors == expected
    assert row_of(stored_asset) == before


def test_an_active_asset_accepts_the_same_location_and_radius(stored_asset):
    activate(stored_asset)

    modify(
        stored_asset,
        title="Martillo",
        latitude=40.4168,
        longitude=-3.7038,
        privacy_radius=1000,
    )

    stored = Asset.objects.get(pk=stored_asset.pk)
    assert (stored.title, stored.updated_at) == ("Martillo", LATER)


def test_a_paused_asset_accepts_a_new_location_and_radius(stored_asset):
    modify(stored_asset, privacy_radius=2000, **MOVED)

    stored = Asset.objects.get(pk=stored_asset.pk)
    assert stored.privacy_radius == 2000
    assert stored.exact_location.coords == (-3.6, 40.5)


@pytest.mark.parametrize(
    ("changes", "expected"), COLUMNS_OF_THE_UPDATE.values(), ids=COLUMNS_OF_THE_UPDATE
)
def test_only_the_changed_columns_are_written(stored_asset, changes, expected):
    if changes.get("category_id") == "kayak":
        changes = {"category_id": Category.objects.get(slug="kayak").pk}

    with CaptureQueriesContext(connection) as captured:
        modify(stored_asset, **changes)

    (update,) = updates_of(captured)
    assert columns_of(update) == expected


def test_a_check_violation_is_translated_without_the_original_error(
    monkeypatch, stored_asset
):
    monkeypatch.setattr(
        "apps.assets.services.clean_price", lambda raw: (Decimal("0.00"), [])
    )
    before = row_of(stored_asset)

    with pytest.raises(DomainValidationError) as caught:
        modify(stored_asset, price="20")

    assert caught.value.message_dict == {"price": ["price_out_of_range"]}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert row_of(stored_asset) == before


def test_a_failed_approximation_is_reported_and_nothing_changes(
    monkeypatch, stored_asset
):
    def fail(latitude, longitude, radius):
        raise ApproximationError("projection_failed")

    monkeypatch.setattr("apps.assets.services.approximate_location", fail)
    before = row_of(stored_asset)

    with pytest.raises(DomainValidationError) as caught:
        modify(stored_asset, **MOVED)

    assert caught.value.message_dict == {"__all__": ["approximation_failed"]}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert row_of(stored_asset) == before
