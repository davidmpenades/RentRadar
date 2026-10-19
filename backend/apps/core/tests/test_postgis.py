import pytest
from django.db import connection

MADRID = (-3.7038, 40.4168)
BARCELONA = (2.1734, 41.3851)
EXPECTED_KM = 505


@pytest.mark.django_db
def test_geography_distance_madrid_barcelona():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ST_Distance("
            "ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,"
            "ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)",
            [*MADRID, *BARCELONA],
        )
        meters = cursor.fetchone()[0]
    assert meters / 1000 == pytest.approx(EXPECTED_KM, rel=0.01)


@pytest.mark.django_db
def test_postgis_comes_from_core_migration():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM django_migrations"
            " WHERE app = 'core' AND name = '0001_postgis_extension'"
        )
        assert cursor.fetchone() is not None
