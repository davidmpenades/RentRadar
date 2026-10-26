import math
import random
import struct

import psycopg.errors
import pytest
from django.core.management import call_command
from django.db import DataError, IntegrityError, connection, connections, transaction
from django.db.migrations.recorder import MigrationRecorder

from apps.categories.models import Category
from conftest import NetworkBlockedError

COERCED_NOTICE = (
    "Coordinate values were coerced into range [-180 -90, 180 90] for GEOGRAPHY"
)
# Fila de una tabla intermedia de users con las dos claves ajenas sin destino
ORPHAN_ROW = "INSERT INTO users_user_groups (user_id, group_id) VALUES (-1, -1)"


def point_as_text(x, y):
    return f"SRID=4326;POINT({format(x, '.17g')} {format(y, '.17g')})"


def point_as_ewkb(x, y):
    # Little endian, tipo punto con SRID incluido y SRID 4326
    return struct.pack("<BIIdd", 1, 0x20000001, 4326, x, y)


# Cómo llega un punto a la BD: marcador del SQL y codificación del parámetro
POINT_FORMS = {
    "text": ("%s::geography", point_as_text),
    "wkb": ("ST_GeogFromWKB(%s)", point_as_ewkb),
}


@pytest.fixture
def places(db):
    with connection.cursor() as cursor:
        cursor.execute("CREATE TEMP TABLE places (g geography(Point, 4326))")


@pytest.fixture
def range_checked_places(db):
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TEMP TABLE range_checked_places ("
            "g geography(Point, 4326),"
            " CONSTRAINT coordinates_in_range CHECK ("
            "ST_X(g::geometry) BETWEEN -180 AND 180"
            " AND ST_Y(g::geometry) BETWEEN -90 AND 90))"
        )


@pytest.fixture
def notices(db):
    received = []

    def keep(diagnostic):
        received.append(diagnostic.message_primary)

    connection.ensure_connection()
    connection.connection.add_notice_handler(keep)
    yield received
    connection.connection.remove_notice_handler(keep)


def store_point(form, x, y, table="places"):
    placeholder, encode = POINT_FORMS[form]
    with connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {table} (g) VALUES ({placeholder})"
            " RETURNING ST_X(g::geometry), ST_Y(g::geometry)",
            [encode(x, y)],
        )
        return cursor.fetchone()


def orphan_raises_at_once():
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(ORPHAN_ROW)
            transaction.set_rollback(True)
    except IntegrityError:
        return True
    return False


@pytest.mark.django_db
@pytest.mark.parametrize("form", POINT_FORMS)
@pytest.mark.parametrize(
    ("x", "y", "stored"),
    [
        (181, 91, (-179, 89)),
        (-181, -91, (179, -89)),
        (3, 91, (3, 89)),
        (181, 3, (-179, 3)),
    ],
)
def test_geography_coerces_out_of_range_coordinates_with_a_fixed_notice(
    places, notices, form, x, y, stored
):
    assert store_point(form, x, y) == stored
    assert notices == [COERCED_NOTICE]


@pytest.mark.django_db
@pytest.mark.parametrize("form", POINT_FORMS)
@pytest.mark.parametrize(("x", "y"), [(math.nan, 3), (3, math.nan)])
def test_geography_stores_nan_as_is_without_notice(places, notices, form, x, y):
    stored = store_point(form, x, y)
    assert [math.isnan(coordinate) for coordinate in stored] == [
        math.isnan(x),
        math.isnan(y),
    ]
    assert [coordinate for coordinate in stored if not math.isnan(coordinate)] == [3]
    assert notices == []


# En PostgreSQL NaN es mayor que cualquier número: el CHECK de rango lo rechaza
@pytest.mark.django_db
@pytest.mark.parametrize("form", POINT_FORMS)
@pytest.mark.parametrize(("x", "y"), [(math.nan, 3), (3, math.nan)])
def test_range_check_rejects_nan_coordinates(range_checked_places, form, x, y):
    with pytest.raises(IntegrityError) as caught, transaction.atomic():
        store_point(form, x, y, table="range_checked_places")
    assert isinstance(caught.value.__cause__, psycopg.errors.CheckViolation)
    assert caught.value.__cause__.diag.constraint_name == "coordinates_in_range"


@pytest.mark.django_db
@pytest.mark.parametrize("form", POINT_FORMS)
def test_range_check_accepts_finite_and_coerced_coordinates(range_checked_places, form):
    table = "range_checked_places"
    assert store_point(form, 3, 40, table=table) == (3, 40)
    assert store_point(form, 181, 91, table=table) == (-179, 89)


@pytest.mark.django_db
def test_geography_accepts_point_empty_and_geometry_has_no_y(places):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO places (g) VALUES ('SRID=4326;POINT EMPTY')"
            " RETURNING ST_IsEmpty(g::geometry), ST_Y(g::geometry)"
        )
        assert cursor.fetchone() == (True, None)


@pytest.mark.django_db
def test_numeric_7_2_overflow_is_a_data_error_without_the_value():
    with (
        pytest.raises(DataError) as caught,
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT 100000::numeric(7,2)")
    assert isinstance(caught.value.__cause__, psycopg.errors.NumericValueOutOfRange)
    assert "100000" not in str(caught.value)


@pytest.mark.django_db
def test_numeric_8_2_admits_one_hundred_thousand():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 100000::numeric(8,2)")
        assert str(cursor.fetchone()[0]) == "100000.00"


@pytest.mark.django_db
@pytest.mark.parametrize("table", ["auth_group_permissions", "users_user_groups"])
def test_django_foreign_keys_are_deferrable_initially_deferred(table):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT condeferrable, condeferred FROM pg_constraint"
            " WHERE contype = 'f' AND conrelid = %s::regclass",
            [table],
        )
        modes = cursor.fetchall()
    assert modes
    assert set(modes) == {(True, True)}


seeded_random = random.Random(5)
ROUND_TRIP_VALUES = [
    0.1,
    -3.7038,
    40.41678123456789,
    1 / 3,
    179.99999999999997,
    -89.99999999999999,
    *[seeded_random.uniform(-180, 180) for _ in range(200)],
]


@pytest.mark.django_db
@pytest.mark.parametrize("form", POINT_FORMS)
def test_geography_round_trip_returns_the_same_float(form):
    placeholder, encode = POINT_FORMS[form]
    returned = []
    with connection.cursor() as cursor:
        for value in ROUND_TRIP_VALUES:
            cursor.execute(f"SELECT ST_AsBinary({placeholder})", [encode(value, 40.4)])
            _, _, x, _ = struct.unpack("<BIdd", bytes(cursor.fetchone()[0]))
            returned.append(x)
    assert returned == ROUND_TRIP_VALUES


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_second_connection_cannot_open_under_the_network_block():
    second = connections.create_connection("default")
    try:
        # psycopg resuelve el nombre del servidor en Python, donde el fixture corta
        with pytest.raises(NetworkBlockedError):
            second.ensure_connection()
    finally:
        second.close()


def seed_state():
    applied = MigrationRecorder(connection).applied_migrations()
    return Category.objects.count(), ("categories", "0002_seed_categories") in applied


@pytest.mark.django_db
def test_seed_rollback_inside_a_reverted_atomic_leaves_the_seed_in_place():
    with transaction.atomic():
        call_command("migrate", "categories", "0001_initial", verbosity=0)
        assert seed_state() == (0, False)
        transaction.set_rollback(True)
    assert seed_state() == (11, True)


@pytest.mark.django_db
def test_deferred_foreign_key_violation_surfaces_at_set_constraints_immediate():
    with (
        pytest.raises(IntegrityError) as caught,
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(ORPHAN_ROW)
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert isinstance(caught.value.__cause__, psycopg.errors.ForeignKeyViolation)


@pytest.mark.django_db
@pytest.mark.parametrize("entry_mode", ["DEFERRED", "IMMEDIATE"])
def test_reverted_savepoint_restores_the_constraint_mode_it_had_on_entry(entry_mode):
    with connection.cursor() as cursor:
        cursor.execute(f"SET CONSTRAINTS ALL {entry_mode}")
    with (
        pytest.raises(IntegrityError),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        cursor.execute(ORPHAN_ROW)
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert orphan_raises_at_once() == (entry_mode == "IMMEDIATE")


@pytest.mark.django_db
def test_set_constraints_immediate_outlives_a_savepoint_that_ends_well():
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert orphan_raises_at_once()


@pytest.mark.django_db
def test_set_constraints_deferred_after_immediate_restores_deferral():
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
    assert not orphan_raises_at_once()
