import math
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from django.contrib.gis.geos import Point

from apps.assets.location import PRIVACY_RADII, ApproximationError, approximate_location
from apps.assets.models import Asset
from apps.assets.rules import COHERENCE_LATITUDE, COHERENCE_LONGITUDE
from apps.assets.services import ERROR_CODES, create_asset
from apps.core.errors import DomainValidationError

BOX_CORNERS = [
    (latitude, longitude)
    for latitude in COHERENCE_LATITUDE
    for longitude in COHERENCE_LONGITUDE
]

EXPECTED_ERROR_CODES = {
    "owner_required",
    "owner_invalid",
    "owner_not_found",
    "category_required",
    "category_invalid",
    "category_not_found",
    "title_required",
    "title_invalid",
    "title_too_short",
    "title_too_long",
    "title_control_char",
    "title_format_char",
    "description_required",
    "description_invalid",
    "description_too_short",
    "description_too_long",
    "description_control_char",
    "description_format_char",
    "price_required",
    "price_invalid",
    "price_out_of_range",
    "price_too_precise",
    "currency_invalid",
    "price_unit_required",
    "price_unit_invalid",
    "privacy_radius_invalid",
    "status_invalid",
    "location_required",
    "location_invalid",
    "location_out_of_range",
    "location_outside_bounds",
    "approximation_failed",
    "constraint_violated",
    "asset_not_found",
    "location_locked",
    "privacy_radius_locked",
}
REQUIRED_ARGUMENTS = [
    ("owner_id", "owner"),
    ("category_id", "category"),
    ("title", "title"),
    ("description", "description"),
    ("price", "price"),
    ("price_unit", "price_unit"),
]
MISSING_COORDINATES = {
    "no_latitude": ("latitude",),
    "no_longitude": ("longitude",),
    "neither": ("latitude", "longitude"),
}
INVALID_FIELDS = {
    "owner_is_bool": ({"owner_id": True}, {"owner": ["owner_invalid"]}),
    "category_is_text": ({"category_id": "5"}, {"category": ["category_invalid"]}),
    "title_too_short": ({"title": "ab"}, {"title": ["title_too_short"]}),
    "title_not_text": ({"title": 5}, {"title": ["title_invalid"]}),
    "description_too_short": (
        {"description": "a" * 19},
        {"description": ["description_too_short"]},
    ),
    "price_is_float": ({"price": 0.1}, {"price": ["price_invalid"]}),
    "price_out_of_range": ({"price": "100000"}, {"price": ["price_out_of_range"]}),
    "price_too_precise": ({"price": "12.345"}, {"price": ["price_too_precise"]}),
    "currency": ({"currency": "USD"}, {"currency": ["currency_invalid"]}),
    "price_unit": ({"price_unit": "night"}, {"price_unit": ["price_unit_invalid"]}),
    "privacy_radius": (
        {"privacy_radius": 1500},
        {"privacy_radius": ["privacy_radius_invalid"]},
    ),
    "active_on_creation": ({"status": "active"}, {"status": ["status_invalid"]}),
    "latitude_is_text": ({"latitude": "40.4"}, {"location": ["location_invalid"]}),
    "latitude_out_of_range": (
        {"latitude": 91.0},
        {"location": ["location_out_of_range"]},
    ),
    "swapped_coordinates": (
        {"latitude": -3.7038, "longitude": 40.4168},
        {"location": ["location_outside_bounds"]},
    ),
}
DEFAULTED_ARGUMENTS = [
    ("currency", "currency_invalid"),
    ("privacy_radius", "privacy_radius_invalid"),
    ("status", "status_invalid"),
]
MISSING_REFERENCES = [
    ("owner_id", "owner", "owner_not_found"),
    ("category_id", "category", "category_not_found"),
]
FORBIDDEN_ARGUMENTS = {
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


def creation_errors(arguments):
    with pytest.raises(DomainValidationError) as caught:
        create_asset(**arguments)
    errors = caught.value.message_dict
    assert {code for codes in errors.values() for code in codes} <= ERROR_CODES
    return errors


def test_the_error_codes_are_the_ones_of_the_catalog():
    assert ERROR_CODES == EXPECTED_ERROR_CODES


def test_a_valid_asset_is_created_paused_with_the_defaults(creation_arguments):
    asset = create_asset(**creation_arguments)

    stored = Asset.objects.get(pk=asset.pk)
    assert Asset.objects.count() == 1
    assert (stored.owner_id, stored.category_id) == (
        creation_arguments["owner_id"],
        creation_arguments["category_id"],
    )
    assert (stored.title, stored.price_unit) == ("Taladro", "day")
    assert stored.price == Decimal("12.34")
    assert (stored.currency, stored.privacy_radius, stored.status) == (
        "EUR",
        1000,
        "paused",
    )


def test_explicit_values_equal_to_the_defaults_are_accepted(creation_arguments):
    creation_arguments.update(currency="EUR", privacy_radius=500, status="paused")

    stored = Asset.objects.get(pk=create_asset(**creation_arguments).pk)

    assert (stored.currency, stored.privacy_radius, stored.status) == (
        "EUR",
        500,
        "paused",
    )


def test_text_and_price_are_stored_normalised(creation_arguments):
    creation_arguments.update(
        title="  Taladro  ",
        description="Cafe" + chr(0x301) + " para el taladro de percusion",
        price="12.340",
    )

    stored = Asset.objects.get(pk=create_asset(**creation_arguments).pk)

    assert stored.title == "Taladro"
    assert stored.description == "Caf" + chr(0xE9) + " para el taladro de percusion"
    assert str(stored.price) == "12.34"


def test_the_dates_are_the_received_now_in_utc(creation_arguments):
    local = datetime(2026, 10, 27, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    creation_arguments["now"] = local

    asset = create_asset(**creation_arguments)

    for saved in (asset, Asset.objects.get(pk=asset.pk)):
        assert saved.created_at == local
        assert saved.updated_at == local
        assert saved.created_at.utcoffset() == timedelta(0)
        assert saved.updated_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_the_public_location_is_derived_from_the_exact_one(creation_arguments, radius):
    creation_arguments["privacy_radius"] = radius

    asset = create_asset(**creation_arguments)

    public_latitude, public_longitude = approximate_location(40.4168, -3.7038, radius)
    for saved in (asset, Asset.objects.get(pk=asset.pk)):
        assert saved.exact_location.coords == (-3.7038, 40.4168)
        assert saved.public_location.coords == (public_longitude, public_latitude)
        assert saved.public_location.coords != saved.exact_location.coords


def is_inside_the_box(latitude, longitude):
    return (
        COHERENCE_LATITUDE[0] <= latitude <= COHERENCE_LATITUDE[1]
        and COHERENCE_LONGITUDE[0] <= longitude <= COHERENCE_LONGITUDE[1]
    )


@pytest.mark.parametrize("radius", PRIVACY_RADII)
@pytest.mark.parametrize(("latitude", "longitude"), BOX_CORNERS)
def test_an_asset_in_a_corner_keeps_its_derived_public_location(
    creation_arguments, latitude, longitude, radius
):
    creation_arguments.update(
        latitude=latitude, longitude=longitude, privacy_radius=radius
    )

    asset = create_asset(**creation_arguments)

    public_latitude, public_longitude = approximate_location(
        latitude, longitude, radius
    )
    saved = Asset.objects.get(pk=asset.pk)
    assert saved.public_location.coords == (public_longitude, public_latitude)
    assert not saved.public_location.empty


def test_the_public_location_of_some_corners_falls_outside_the_box():
    # Sin esto el test de las esquinas pasaría igual si la pública siempre cayera dentro
    outside = [
        (latitude, longitude, radius)
        for latitude, longitude in BOX_CORNERS
        for radius in PRIVACY_RADII
        if not is_inside_the_box(*approximate_location(latitude, longitude, radius))
    ]

    assert outside


@pytest.mark.parametrize(("argument", "code"), DEFAULTED_ARGUMENTS)
def test_an_explicit_none_does_not_take_the_default(creation_arguments, argument, code):
    creation_arguments[argument] = None

    assert creation_errors(creation_arguments) == {argument: [code]}


@pytest.mark.parametrize("how", ["omitted", "none"])
@pytest.mark.parametrize(("argument", "field"), REQUIRED_ARGUMENTS)
def test_a_missing_required_field_gets_its_required_code(
    creation_arguments, argument, field, how
):
    if how == "omitted":
        del creation_arguments[argument]
    else:
        creation_arguments[argument] = None

    assert creation_errors(creation_arguments) == {field: [f"{field}_required"]}


@pytest.mark.parametrize("how", ["omitted", "none"])
@pytest.mark.parametrize("names", MISSING_COORDINATES.values(), ids=MISSING_COORDINATES)
def test_a_missing_coordinate_gets_the_location_required_code(
    creation_arguments, names, how
):
    for name in names:
        if how == "omitted":
            del creation_arguments[name]
        else:
            creation_arguments[name] = None

    assert creation_errors(creation_arguments) == {"location": ["location_required"]}


@pytest.mark.parametrize(
    ("overrides", "expected"), INVALID_FIELDS.values(), ids=INVALID_FIELDS
)
def test_an_invalid_field_gets_its_code_without_touching_the_database(
    creation_arguments, django_assert_num_queries, overrides, expected
):
    creation_arguments.update(overrides)

    with django_assert_num_queries(0):
        errors = creation_errors(creation_arguments)

    assert errors == expected
    assert Asset.objects.count() == 0


def test_several_invalid_fields_are_reported_together(creation_arguments):
    creation_arguments.update(
        title="ab", price="0", status="active", latitude=None, owner_id=None
    )

    assert creation_errors(creation_arguments) == {
        "owner": ["owner_required"],
        "title": ["title_too_short"],
        "price": ["price_out_of_range"],
        "status": ["status_invalid"],
        "location": ["location_required"],
    }


@pytest.mark.parametrize(("argument", "field", "code"), MISSING_REFERENCES)
def test_a_missing_reference_is_reported_and_nothing_is_created(
    creation_arguments, argument, field, code
):
    creation_arguments[argument] = 999_999_999

    assert creation_errors(creation_arguments) == {field: [code]}
    assert Asset.objects.count() == 0


def test_both_missing_references_are_reported_together(creation_arguments):
    creation_arguments.update(owner_id=999_999_999, category_id=999_999_998)

    assert creation_errors(creation_arguments) == {
        "owner": ["owner_not_found"],
        "category": ["category_not_found"],
    }


@pytest.mark.parametrize(("argument", "field", "code"), MISSING_REFERENCES)
def test_a_foreign_key_violation_is_translated_by_the_forced_check(
    monkeypatch, creation_arguments, argument, field, code
):
    monkeypatch.setattr(
        "apps.assets.services._missing_references", lambda owner_id, category_id: {}
    )
    creation_arguments[argument] = 999_999_999

    with pytest.raises(DomainValidationError) as caught:
        create_asset(**creation_arguments)

    assert caught.value.message_dict == {field: [code]}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert Asset.objects.count() == 0


def test_a_check_violation_is_translated_without_the_original_error(
    monkeypatch, creation_arguments
):
    monkeypatch.setattr(
        "apps.assets.services.clean_price", lambda raw: (Decimal("0.00"), [])
    )

    with pytest.raises(DomainValidationError) as caught:
        create_asset(**creation_arguments)

    assert caught.value.message_dict == {"price": ["price_out_of_range"]}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert Asset.objects.count() == 0


def test_a_violation_of_the_public_location_is_an_unmapped_constraint(
    monkeypatch, creation_arguments
):
    monkeypatch.setattr(
        "apps.assets.services.approximate_location",
        lambda latitude, longitude, radius: (math.nan, 0.0),
    )

    with pytest.raises(DomainValidationError) as caught:
        create_asset(**creation_arguments)

    assert caught.value.message_dict == {"__all__": ["constraint_violated"]}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert Asset.objects.count() == 0


def test_a_failed_approximation_is_reported_and_nothing_is_created(
    monkeypatch, creation_arguments
):
    def fail(latitude, longitude, radius):
        raise ApproximationError("projection_failed")

    monkeypatch.setattr("apps.assets.services.approximate_location", fail)

    with pytest.raises(DomainValidationError) as caught:
        create_asset(**creation_arguments)

    assert caught.value.message_dict == {"__all__": ["approximation_failed"]}
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert Asset.objects.count() == 0


@pytest.mark.parametrize(
    ("name", "value"), FORBIDDEN_ARGUMENTS.items(), ids=FORBIDDEN_ARGUMENTS
)
def test_an_argument_outside_the_whitelist_is_a_programming_error(
    creation_arguments, name, value
):
    creation_arguments[name] = value

    with pytest.raises(TypeError) as caught:
        create_asset(**creation_arguments)

    assert name in str(caught.value)
    assert "3.7038123" not in str(caught.value)
    assert "40.4168456" not in str(caught.value)
    assert Asset.objects.count() == 0


def test_the_arguments_are_keyword_only(creation_arguments):
    with pytest.raises(TypeError):
        create_asset(creation_arguments["now"])


def test_now_is_required(creation_arguments):
    del creation_arguments["now"]

    with pytest.raises(TypeError):
        create_asset(**creation_arguments)


@pytest.mark.parametrize("now", INVALID_NOW.values(), ids=INVALID_NOW)
def test_a_now_without_a_time_zone_is_a_programming_error(
    creation_arguments, django_assert_num_queries, now
):
    creation_arguments["now"] = now

    with django_assert_num_queries(0), pytest.raises(ValueError) as caught:
        create_asset(**creation_arguments)

    assert str(caught.value) == "now_not_aware"
    assert Asset.objects.count() == 0
