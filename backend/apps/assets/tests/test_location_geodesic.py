import pytest
from django.db import connection

from apps.assets.location import (
    PRIVACY_RADII,
    _project,
    _unproject,
    approximate_location,
    grid_cell_centre,
)

pytestmark = pytest.mark.django_db

# ST_Distance sobre geography mide en metros sobre el esferoide
GEODESIC_DISTANCES = """
SELECT ST_Distance(
    ST_SetSRID(ST_MakePoint(from_lon, from_lat), 4326)::geography,
    ST_SetSRID(ST_MakePoint(to_lon, to_lat), 4326)::geography
)
FROM unnest(%s::float8[], %s::float8[], %s::float8[], %s::float8[])
    WITH ORDINALITY AS pair(from_lat, from_lon, to_lat, to_lon, position)
ORDER BY position
"""


def geodesic_distances(pairs):
    columns = zip(*[(*start, *end) for start, end in pairs], strict=True)
    with connection.cursor() as cursor:
        cursor.execute(GEODESIC_DISTANCES, [list(column) for column in columns])
        return [row[0] for row in cursor.fetchall()]


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_the_exact_point_stays_within_the_radius_of_the_public_one(
    radius, sample_points
):
    pairs = [
        ((latitude, longitude), approximate_location(latitude, longitude, radius))
        for latitude, longitude in sample_points
    ]
    assert max(geodesic_distances(pairs)) <= radius


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_cell_sides_measure_between_95_and_105_percent_of_the_radius(
    radius, sample_points
):
    pairs = []
    for latitude, longitude in sample_points:
        east, north = _project(latitude, longitude)
        centre_east, centre_north = grid_cell_centre(east, north, radius)
        lower_east = centre_east - radius / 2
        lower_north = centre_north - radius / 2
        corner = _unproject(lower_east, lower_north)
        pairs.append((corner, _unproject(lower_east + radius, lower_north)))
        pairs.append((corner, _unproject(lower_east, lower_north + radius)))
    ratios = [distance / radius for distance in geodesic_distances(pairs)]
    assert min(ratios) >= 0.95
    assert max(ratios) <= 1.05
