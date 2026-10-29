import math
from datetime import UTC, datetime
from decimal import Decimal

import psycopg.errors
import pytest
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import GEOSGeometry, Point
from django.db import IntegrityError, connection, models, transaction
from django.db.models import ProtectedError

from apps.assets.models import Asset, AssetStatus, PriceUnit
from apps.assets.rules import PRICE_UNITS, STATUSES_ON_UPDATE
from apps.assets.tests.conftest import (
    SENTINEL_LATITUDE,
    SENTINEL_LONGITUDE,
    coordinate_forms,
)
from apps.categories.models import Category
from apps.users.models import User

CHECK_NAMES = {
    "assets_asset_title_length",
    "assets_asset_description_length",
    "assets_asset_price_range",
    "assets_asset_currency_eur",
    "assets_asset_price_unit_valid",
    "assets_asset_privacy_radius_valid",
    "assets_asset_status_valid",
    "assets_asset_exact_location_valid",
    "assets_asset_public_location_valid",
}
CHECK_VIOLATIONS = {
    "title_too_short": ({"title": "ab"}, "assets_asset_title_length"),
    "title_too_long": ({"title": "a" * 101}, "assets_asset_title_length"),
    "description_too_short": (
        {"description": "a" * 19},
        "assets_asset_description_length",
    ),
    "description_too_long": (
        {"description": "a" * 2001},
        "assets_asset_description_length",
    ),
    "price_zero": ({"price": Decimal("0")}, "assets_asset_price_range"),
    "price_too_high": ({"price": Decimal("100000")}, "assets_asset_price_range"),
    "currency": ({"currency": "USD"}, "assets_asset_currency_eur"),
    "price_unit": ({"price_unit": "night"}, "assets_asset_price_unit_valid"),
    "privacy_radius": ({"privacy_radius": 1500}, "assets_asset_privacy_radius_valid"),
    "status": ({"status": "deleted"}, "assets_asset_status_valid"),
}
LOCATION_FIELDS = [
    ("exact_location", "assets_asset_exact_location_valid"),
    ("public_location", "assets_asset_public_location_valid"),
]
UNUSABLE_POINTS = {
    "nan_latitude": Point(-3.7, math.nan, srid=4326),
    "nan_longitude": Point(math.nan, 40.4, srid=4326),
    "empty": GEOSGeometry("SRID=4326;POINT EMPTY"),
}
FOREIGN_KEYS = [
    ("owner_id", "assets_asset_owner_id_23c9aaf7_fk_users_user_id"),
    ("category_id", "assets_asset_category_id_b30c6baf_fk_categories_category_id"),
]
EXPECTED_FIELDS = {
    "id": models.BigAutoField,
    "owner": models.ForeignKey,
    "category": models.ForeignKey,
    "title": models.TextField,
    "description": models.TextField,
    "price": models.DecimalField,
    "currency": models.TextField,
    "price_unit": models.TextField,
    "exact_location": gis_models.PointField,
    "public_location": gis_models.PointField,
    "privacy_radius": models.IntegerField,
    "status": models.TextField,
    "created_at": models.DateTimeField,
    "updated_at": models.DateTimeField,
}
# Tipo de cada columna en PostgreSQL
EXPECTED_COLUMNS = {
    "id": "int8",
    "owner_id": "int8",
    "category_id": "int8",
    "title": "text",
    "description": "text",
    "price": "numeric",
    "currency": "text",
    "price_unit": "text",
    "exact_location": "geography",
    "public_location": "geography",
    "privacy_radius": "int4",
    "status": "text",
    "created_at": "timestamptz",
    "updated_at": "timestamptz",
}
EMOJI = chr(0x1F600)


def violated_constraint(caught):
    return caught.value.__cause__.diag.constraint_name


def test_the_model_has_exactly_these_fields():
    fields = {field.name: type(field) for field in Asset._meta.concrete_fields}

    assert fields == EXPECTED_FIELDS


def test_no_field_is_nullable_or_has_a_default():
    for field in Asset._meta.concrete_fields:
        assert field.null is False, field.name
        assert field.has_default() is False, field.name


def test_dates_are_set_by_the_caller_and_not_by_the_model():
    for name in ("created_at", "updated_at"):
        field = Asset._meta.get_field(name)
        assert field.auto_now is False
        assert field.auto_now_add is False


def test_price_has_eight_digits_and_two_decimals():
    field = Asset._meta.get_field("price")

    assert (field.max_digits, field.decimal_places) == (8, 2)


@pytest.mark.parametrize(("name", "model"), [("owner", User), ("category", Category)])
def test_foreign_keys_protect_and_have_no_reverse_accessor(name, model):
    field = Asset._meta.get_field(name)

    assert field.remote_field.model is model
    assert field.remote_field.on_delete is models.PROTECT
    assert field.remote_field.related_name == "+"


@pytest.mark.parametrize(
    ("name", "indexed"), [("exact_location", False), ("public_location", True)]
)
def test_locations_are_geography_points_and_only_the_public_one_is_indexed(
    name, indexed
):
    field = Asset._meta.get_field(name)

    assert field.geography is True
    assert field.srid == 4326
    assert field.spatial_index is indexed


def test_choices_match_the_closed_lists_of_the_rules():
    assert tuple(PriceUnit.values) == PRICE_UNITS
    assert tuple(AssetStatus.values) == STATUSES_ON_UPDATE
    assert Asset._meta.get_field("price_unit").choices == PriceUnit.choices
    assert Asset._meta.get_field("status").choices == AssetStatus.choices


def test_the_constraints_are_the_nine_named_checks():
    constraints = Asset._meta.constraints

    assert all(
        isinstance(constraint, models.CheckConstraint) for constraint in constraints
    )
    assert {constraint.name for constraint in constraints} == CHECK_NAMES
    assert len(constraints) == len(CHECK_NAMES)


def test_str_and_repr_show_the_title_and_the_id_and_no_coordinates():
    asset = Asset(
        id=5,
        title="Taladro",
        exact_location=Point(SENTINEL_LONGITUDE, SENTINEL_LATITUDE, srid=4326),
        public_location=Point(SENTINEL_LONGITUDE, SENTINEL_LATITUDE, srid=4326),
    )

    assert str(asset) == "Taladro (5)"
    for text in (str(asset), repr(asset)):
        assert "Taladro" in text
        assert "5" in text
        for form in coordinate_forms(SENTINEL_LONGITUDE, SENTINEL_LATITUDE):
            assert form not in text


def test_a_valid_asset_is_saved_and_read_back(make_asset, owner, category):
    asset = make_asset()
    asset.save()

    stored = Asset.objects.get(pk=asset.pk)

    assert (stored.owner_id, stored.category_id) == (owner.pk, category.pk)
    assert stored.title == "Taladro"
    assert stored.description == "Taladro de percusion en buen estado"
    assert stored.price == Decimal("12.34")
    assert (stored.currency, stored.price_unit) == ("EUR", "day")
    assert stored.exact_location.coords == (-3.7038, 40.4168)
    assert stored.public_location.coords == (-3.7052, 40.4157)
    assert (stored.privacy_radius, stored.status) == (1000, "paused")
    assert stored.created_at == datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    assert stored.updated_at == stored.created_at


@pytest.mark.parametrize(
    ("overrides", "name"), CHECK_VIOLATIONS.values(), ids=CHECK_VIOLATIONS.keys()
)
def test_each_check_rejects_its_violation_by_name(make_asset, overrides, name):
    asset = make_asset(**overrides)

    with pytest.raises(IntegrityError) as caught, transaction.atomic():
        asset.save()

    assert violated_constraint(caught) == name


def test_the_length_checks_count_code_points_and_not_bytes(make_asset):
    make_asset(title=EMOJI * 100).save()

    with pytest.raises(IntegrityError) as caught, transaction.atomic():
        make_asset(title=EMOJI * 101).save()

    assert violated_constraint(caught) == "assets_asset_title_length"


@pytest.mark.parametrize(("field", "name"), LOCATION_FIELDS)
@pytest.mark.parametrize("point", UNUSABLE_POINTS.values(), ids=UNUSABLE_POINTS.keys())
def test_a_non_finite_or_empty_location_is_rejected_by_name(
    make_asset, field, name, point
):
    asset = make_asset(**{field: point})

    with pytest.raises(IntegrityError) as caught, transaction.atomic():
        asset.save()

    assert violated_constraint(caught) == name


@pytest.mark.parametrize("field", ["exact_location", "public_location"])
def test_a_null_location_is_rejected_as_not_null(make_asset, field):
    asset = make_asset(**{field: None})

    with pytest.raises(IntegrityError) as caught, transaction.atomic():
        asset.save()

    assert isinstance(caught.value.__cause__, psycopg.errors.NotNullViolation)


@pytest.mark.parametrize("field", ["exact_location", "public_location"])
def test_out_of_range_coordinates_are_adjusted_by_the_type_and_not_rejected(
    make_asset, field
):
    asset = make_asset(**{field: Point(181.0, 91.0, srid=4326)})
    asset.save()

    assert getattr(Asset.objects.get(pk=asset.pk), field).coords == (-179.0, 89.0)


@pytest.mark.parametrize(("field", "name"), FOREIGN_KEYS)
def test_a_missing_reference_violates_its_foreign_key_by_name(make_asset, field, name):
    asset = make_asset()
    setattr(asset, field, 999_999_999)

    with pytest.raises(IntegrityError) as caught, transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        asset.save()

    assert violated_constraint(caught) == name


def test_deleting_an_owner_with_assets_is_protected(make_asset, owner):
    make_asset().save()

    with pytest.raises(ProtectedError):
        owner.delete()

    assert User.objects.filter(pk=owner.pk).exists()


def test_deleting_a_category_with_assets_is_protected(make_asset, category):
    make_asset().save()

    with pytest.raises(ProtectedError):
        category.delete()

    assert Category.objects.filter(pk=category.pk).exists()


def test_only_the_public_location_has_a_spatial_index(db):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT indexdef FROM pg_indexes WHERE tablename = 'assets_asset'"
        )
        definitions = [row[0] for row in cursor.fetchall()]

    (spatial,) = [item for item in definitions if "USING gist" in item]
    assert "public_location" in spatial


def test_columns_have_the_expected_types_and_none_is_nullable(db):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, udt_name, is_nullable, numeric_precision,"
            " numeric_scale FROM information_schema.columns"
            " WHERE table_name = 'assets_asset'"
        )
        columns = {row[0]: row[1:] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT f_geography_column, type, srid FROM geography_columns"
            " WHERE f_table_name = 'assets_asset'"
        )
        geographies = sorted(cursor.fetchall())

    assert {name: values[0] for name, values in columns.items()} == EXPECTED_COLUMNS
    assert {values[1] for values in columns.values()} == {"NO"}
    assert columns["price"][2:] == (8, 2)
    assert geographies == [
        ("exact_location", "Point", 4326),
        ("public_location", "Point", 4326),
    ]
