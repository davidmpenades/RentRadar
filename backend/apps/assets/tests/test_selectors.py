import dataclasses
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from django.contrib.gis.geos import Point
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.assets.models import Asset
from apps.assets.selectors import visible_assets_in_zone
from apps.assets.services import create_asset, update_asset
from apps.assets.tests.conftest import NOW
from apps.assets.zone import Zone
from apps.categories.models import Category
from apps.users.models import User

LIMIT = 200
# Desplazamiento fijo de la exacta respecto a la pública en los bienes de este módulo
EXACT_LATITUDE_OFFSET = 0.004
EXACT_LONGITUDE_OFFSET = 0.003
COORDINATE_TOLERANCE = 1e-9
WHITELIST = {
    "public_id",
    "title",
    "category__slug",
    "category__name",
    "price",
    "currency",
    "price_unit",
    "privacy_radius",
    "latitude",
    "longitude",
}
# Posiciones asimétricas: latitud y longitud con valores y signos distintos
MADRID_PUBLIC = (40.4157, -3.7052)
VALENCIA_PUBLIC = (39.4699, -0.3763)
INSIDE = (39.45, -0.35)


def zone_of(south, west, north, east):
    return Zone(*(Decimal(value) for value in (south, west, north, east)))


VALENCIA_ZONE = zone_of("39.4", "-0.4", "39.5", "-0.3")
MADRID_ZONE = zone_of("40.3", "-3.8", "40.5", "-3.6")


@pytest.fixture
def visible_asset(make_asset):
    # Recibe la ubicación pública; la exacta queda desplazada para poder distinguirlas
    def build(latitude, longitude, **overrides):
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
        asset = make_asset(**fields)
        asset.save()
        return asset

    return build


def select(zone, limit=LIMIT):
    return visible_assets_in_zone(zone=zone, limit=limit)


def public_ids_of(zone, limit=LIMIT):
    rows, _ = select(zone, limit)
    return [row["public_id"] for row in rows]


def captured_queries(zone, limit=LIMIT):
    with CaptureQueriesContext(connection) as context:
        select(zone, limit)
    return [query["sql"] for query in context.captured_queries]


def captured_sql(zone, limit=LIMIT):
    queries = captured_queries(zone, limit)
    assert len(queries) == 1
    return queries[0]


def select_clause(sql):
    return sql[: sql.index(" FROM ")]


def where_clause(sql):
    return sql[sql.index(" WHERE ") : sql.index(" ORDER BY ")]


# --- Dentro y fuera de la zona -------------------------------------------------


def test_an_active_asset_inside_the_zone_is_returned_and_one_outside_is_not(
    visible_asset,
):
    inside = visible_asset(*INSIDE)
    visible_asset(41.0, -0.35)
    visible_asset(39.45, 2.0)

    rows, incomplete = select(VALENCIA_ZONE)

    assert [row["public_id"] for row in rows] == [inside.public_id]
    assert incomplete is False


def test_an_empty_database_returns_no_rows_and_is_not_incomplete(db):
    assert select(VALENCIA_ZONE) == ([], False)


EDGES_INSIDE = [
    pytest.param(39.4, -0.35, id="south_edge"),
    pytest.param(39.5, -0.35, id="north_edge"),
    pytest.param(39.45, -0.4, id="west_edge"),
    pytest.param(39.45, -0.3, id="east_edge"),
]
JUST_OUTSIDE_EDGES = [
    pytest.param(39.399999, -0.35, id="below_the_south_edge"),
    pytest.param(39.500001, -0.35, id="above_the_north_edge"),
    pytest.param(39.45, -0.400001, id="west_of_the_west_edge"),
    pytest.param(39.45, -0.299999, id="east_of_the_east_edge"),
]


@pytest.mark.parametrize(("latitude", "longitude"), EDGES_INSIDE)
def test_an_asset_exactly_on_an_edge_of_the_zone_is_returned(
    visible_asset, latitude, longitude
):
    asset = visible_asset(latitude, longitude)

    assert public_ids_of(VALENCIA_ZONE) == [asset.public_id]


@pytest.mark.parametrize(("latitude", "longitude"), JUST_OUTSIDE_EDGES)
def test_an_asset_one_millionth_of_a_degree_outside_an_edge_is_not_returned(
    visible_asset, latitude, longitude
):
    visible_asset(latitude, longitude)

    assert select(VALENCIA_ZONE) == ([], False)


def test_a_zone_with_zero_height_returns_the_assets_on_that_latitude(visible_asset):
    first = visible_asset(39.4, -0.38)
    second = visible_asset(39.4, -0.32)
    visible_asset(39.45, -0.35)
    flat = zone_of("39.4", "-0.4", "39.4", "-0.3")

    assert set(public_ids_of(flat)) == {first.public_id, second.public_id}


def test_a_zone_with_zero_width_returns_the_assets_on_that_longitude(visible_asset):
    first = visible_asset(39.42, -0.35)
    second = visible_asset(39.48, -0.35)
    visible_asset(39.45, -0.32)
    narrow = zone_of("39.4", "-0.35", "39.5", "-0.35")

    assert set(public_ids_of(narrow)) == {first.public_id, second.public_id}


def test_a_zone_of_a_single_point_returns_only_the_assets_at_that_point(visible_asset):
    at_the_point = visible_asset(39.4, -0.35)
    visible_asset(39.4, -0.34)
    visible_asset(39.41, -0.35)
    point = zone_of("39.4", "-0.35", "39.4", "-0.35")

    assert public_ids_of(point) == [at_the_point.public_id]


def test_limits_with_trailing_zeros_give_the_same_result(visible_asset):
    on_the_edge = visible_asset(39.4, -0.4)
    inside = visible_asset(*INSIDE)
    with_zeros = zone_of("39.40", "-0.40", "39.50", "-0.30")

    assert select(with_zeros) == select(VALENCIA_ZONE)
    assert set(public_ids_of(with_zeros)) == {on_the_edge.public_id, inside.public_id}


def test_the_selector_leaves_the_zone_unchanged(visible_asset):
    visible_asset(*INSIDE)
    zone = zone_of("39.40", "-0.40", "39.50", "-0.30")
    before = dataclasses.replace(zone)

    select(zone)

    assert zone == before
    assert [str(value) for value in dataclasses.astuple(zone)] == [
        "39.40",
        "-0.40",
        "39.50",
        "-0.30",
    ]


# --- Qué bienes son visibles ---------------------------------------------------


def test_a_paused_asset_is_not_returned_even_if_its_owner_is_active(visible_asset):
    visible_asset(*INSIDE, status="paused")

    assert select(VALENCIA_ZONE) == ([], False)


def test_an_active_asset_of_an_owner_with_a_deactivated_account_is_not_returned(
    visible_asset,
):
    gone = User.objects.create(email="gone@correo.es", is_active=False)
    visible_asset(*INSIDE, owner=gone)

    assert select(VALENCIA_ZONE) == ([], False)


def test_assets_of_several_owners_are_returned_together(visible_asset):
    other = User.objects.create(email="other@correo.es")
    mine = visible_asset(39.42, -0.35, created_at=NOW)
    theirs = visible_asset(39.48, -0.35, owner=other, created_at=NOW - timedelta(1))

    assert public_ids_of(VALENCIA_ZONE) == [mine.public_id, theirs.public_id]


def test_each_row_carries_the_slug_and_name_of_its_own_category(visible_asset):
    pool = Category.objects.get(slug="pool")
    kayak = Category.objects.get(slug="kayak")
    in_the_pool = visible_asset(39.42, -0.35, category=pool, created_at=NOW)
    in_the_kayak = visible_asset(
        39.48, -0.35, category=kayak, created_at=NOW - timedelta(1)
    )

    rows, _ = select(VALENCIA_ZONE)

    assert [
        (row["public_id"], row["category__slug"], row["category__name"]) for row in rows
    ] == [
        (in_the_pool.public_id, "pool", pool.name),
        (in_the_kayak.public_id, "kayak", kayak.name),
    ]


# --- Exacta y pública en lados opuestos de un borde ----------------------------


def test_an_asset_whose_public_location_is_inside_and_exact_outside_is_returned(
    visible_asset,
):
    asset = visible_asset(
        39.401,
        -0.35,
        exact_location=Point(-0.35, 39.399, srid=4326),
    )

    assert public_ids_of(VALENCIA_ZONE) == [asset.public_id]


def test_an_asset_whose_public_location_is_outside_and_exact_inside_is_not_returned(
    visible_asset,
):
    visible_asset(
        39.399,
        -0.35,
        exact_location=Point(-0.35, 39.401, srid=4326),
    )

    assert select(VALENCIA_ZONE) == ([], False)


# --- Privacidad de lo devuelto -------------------------------------------------


def test_a_row_has_exactly_the_whitelisted_keys(visible_asset):
    visible_asset(*MADRID_PUBLIC)

    rows, _ = select(MADRID_ZONE)

    assert len(rows) == 1
    assert set(rows[0]) == WHITELIST
    assert list(rows[0]).count("latitude") == 1


def test_a_row_has_the_values_and_types_of_the_asset(visible_asset, category):
    asset = visible_asset(*MADRID_PUBLIC)

    (row,), _ = select(MADRID_ZONE)

    assert isinstance(row["public_id"], UUID)
    assert isinstance(row["price"], Decimal)
    assert isinstance(row["latitude"], float)
    assert isinstance(row["longitude"], float)
    assert {key: row[key] for key in WHITELIST - {"latitude", "longitude"}} == {
        "public_id": asset.public_id,
        "title": "Taladro",
        "category__slug": category.slug,
        "category__name": category.name,
        "price": Decimal("12.34"),
        "currency": "EUR",
        "price_unit": "day",
        "privacy_radius": 1000,
    }


def test_the_coordinates_are_the_public_ones_and_not_the_exact_ones(visible_asset):
    asset = visible_asset(*MADRID_PUBLIC)

    (row,), _ = select(MADRID_ZONE)

    assert abs(row["latitude"] - asset.public_location.y) < COORDINATE_TOLERANCE
    assert abs(row["longitude"] - asset.public_location.x) < COORDINATE_TOLERANCE
    assert row["latitude"] == pytest.approx(MADRID_PUBLIC[0], abs=COORDINATE_TOLERANCE)
    assert row["longitude"] == pytest.approx(MADRID_PUBLIC[1], abs=COORDINATE_TOLERANCE)
    assert (
        abs(row["latitude"] - asset.exact_location.y)
        >= EXACT_LATITUDE_OFFSET - COORDINATE_TOLERANCE
    )
    assert (
        abs(row["longitude"] - asset.exact_location.x)
        >= EXACT_LONGITUDE_OFFSET - COORDINATE_TOLERANCE
    )


def test_each_row_carries_its_own_coordinates_without_crossing_the_axes(
    visible_asset,
):
    madrid = visible_asset(*MADRID_PUBLIC, created_at=NOW)
    valencia = visible_asset(*VALENCIA_PUBLIC, created_at=NOW - timedelta(1))
    spain = zone_of("39", "-4", "41", "0")

    rows, _ = select(spain)

    found = {row["public_id"]: (row["latitude"], row["longitude"]) for row in rows}
    assert set(found) == {madrid.public_id, valencia.public_id}
    assert found[madrid.public_id] == pytest.approx(
        MADRID_PUBLIC, abs=COORDINATE_TOLERANCE
    )
    assert found[valencia.public_id] == pytest.approx(
        VALENCIA_PUBLIC, abs=COORDINATE_TOLERANCE
    )


# --- Coherencia con el servicio ------------------------------------------------


@pytest.mark.parametrize("radius", [500, 1000, 2000])
def test_the_coordinates_of_the_selector_match_what_the_service_stored(
    creation_arguments, radius
):
    # Comprueba que servicio y selector hablan de la misma columna, no la privacidad
    created = create_asset(**creation_arguments, privacy_radius=radius)
    update_asset(now=NOW + timedelta(hours=1), asset_id=created.pk, status="active")
    stored = Asset.objects.get(pk=created.pk).public_location

    (row,), _ = select(MADRID_ZONE)

    assert row["public_id"] == created.public_id
    assert abs(row["latitude"] - stored.y) < COORDINATE_TOLERANCE
    assert abs(row["longitude"] - stored.x) < COORDINATE_TOLERANCE


# --- Orden y límite ------------------------------------------------------------


def test_the_assets_come_newest_first(visible_asset):
    middle = visible_asset(*MADRID_PUBLIC, created_at=NOW - timedelta(minutes=5))
    newest = visible_asset(*MADRID_PUBLIC, created_at=NOW)
    oldest = visible_asset(*MADRID_PUBLIC, created_at=NOW - timedelta(minutes=9))

    assert public_ids_of(MADRID_ZONE) == [
        newest.public_id,
        middle.public_id,
        oldest.public_id,
    ]


def test_with_the_same_creation_instant_the_higher_id_comes_first(visible_asset):
    first = visible_asset(*MADRID_PUBLIC, created_at=NOW)
    second = visible_asset(*MADRID_PUBLIC, created_at=NOW)
    third = visible_asset(*MADRID_PUBLIC, created_at=NOW)
    assert first.pk < second.pk < third.pk

    assert public_ids_of(MADRID_ZONE) == [
        third.public_id,
        second.public_id,
        first.public_id,
    ]


@pytest.mark.parametrize(
    ("created", "limit", "returned", "incomplete"),
    [
        pytest.param(5, 3, 3, True, id="more_than_the_limit"),
        pytest.param(3, 3, 3, False, id="exactly_the_limit"),
        pytest.param(2, 3, 2, False, id="fewer_than_the_limit"),
        pytest.param(1, 1, 1, False, id="one_with_a_limit_of_one"),
        pytest.param(2, 1, 1, True, id="two_with_a_limit_of_one"),
    ],
)
def test_the_limit_keeps_the_newest_assets_and_reports_whether_more_exist(
    visible_asset, created, limit, returned, incomplete
):
    assets = [
        visible_asset(*MADRID_PUBLIC, created_at=NOW - timedelta(minutes=minutes))
        for minutes in range(created)
    ]

    rows, reported = select(MADRID_ZONE, limit)

    assert [row["public_id"] for row in rows] == [
        asset.public_id for asset in assets[:returned]
    ]
    assert reported is incomplete


def test_a_limit_of_zero_returns_nothing_and_reports_that_assets_exist(
    visible_asset,
):
    visible_asset(*MADRID_PUBLIC)

    assert select(MADRID_ZONE, 0) == ([], True)


def test_a_limit_of_zero_without_assets_is_not_incomplete(db):
    assert select(MADRID_ZONE, 0) == ([], False)


def bulk_visible_assets(make_asset, count):
    # created_at distinto por bien: el más reciente es el primero de la lista
    assets = [
        make_asset(status="active", created_at=NOW - timedelta(minutes=minutes))
        for minutes in range(count)
    ]
    Asset.objects.bulk_create(assets)
    return assets


def test_two_hundred_and_one_visible_assets_give_two_hundred_rows_and_incomplete(
    make_asset,
):
    assets = bulk_visible_assets(make_asset, LIMIT + 1)

    rows, incomplete = select(MADRID_ZONE, LIMIT)

    assert [row["public_id"] for row in rows] == [
        asset.public_id for asset in assets[:LIMIT]
    ]
    assert incomplete is True


def test_two_hundred_visible_assets_give_two_hundred_rows_and_are_complete(
    make_asset,
):
    assets = bulk_visible_assets(make_asset, LIMIT)

    rows, incomplete = select(MADRID_ZONE, LIMIT)

    assert [row["public_id"] for row in rows] == [asset.public_id for asset in assets]
    assert incomplete is False


# --- SQL capturado -------------------------------------------------------------


@pytest.fixture
def one_visible_asset(visible_asset):
    return visible_asset(*MADRID_PUBLIC)


def test_the_selector_runs_exactly_one_query(one_visible_asset):
    assert len(captured_queries(MADRID_ZONE)) == 1


def test_the_query_is_a_select_with_a_limit_one_above_the_requested_one(
    one_visible_asset,
):
    sql = captured_sql(MADRID_ZONE, LIMIT)

    assert sql.lstrip().startswith("SELECT")
    assert sql.endswith("LIMIT 201")


def test_the_query_does_not_count(one_visible_asset):
    assert "COUNT(" not in captured_sql(MADRID_ZONE).upper()


def test_the_exact_location_appears_nowhere_in_the_query(one_visible_asset):
    assert "exact_location" not in captured_sql(MADRID_ZONE)


def test_the_select_clause_has_no_user_or_owner_columns(one_visible_asset):
    selected = select_clause(captured_sql(MADRID_ZONE))

    assert "users_user" not in selected
    assert "owner" not in selected


@pytest.mark.parametrize(
    "column",
    [
        pytest.param('"assets_asset"."id"', id="id"),
        pytest.param('"assets_asset"."description"', id="description"),
        pytest.param('"assets_asset"."status"', id="status"),
        pytest.param('"assets_asset"."created_at"', id="created_at"),
        pytest.param('"assets_asset"."updated_at"', id="updated_at"),
        pytest.param('"categories_category"."id"', id="category_id"),
    ],
)
def test_the_select_clause_has_no_columns_outside_the_whitelist(
    one_visible_asset, column
):
    assert column not in select_clause(captured_sql(MADRID_ZONE))


def test_the_where_clause_filters_by_the_public_location_in_both_axes(
    one_visible_asset,
):
    where = where_clause(captured_sql(MADRID_ZONE))

    assert "ST_X(" in where
    assert "ST_Y(" in where
    assert "public_location" in where
    assert where.count("BETWEEN") == 2
    assert "is_active" in where
