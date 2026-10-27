import math
from decimal import Decimal

import pytest

from apps.assets import location
from apps.assets.location import (
    PRIVACY_RADII,
    ApproximationError,
    _project,
    _unproject,
    approximate_location,
    grid_cell_centre,
)

INVALID_RADII = [0, -500, 1500, True, "1000", 500.0, None]
INVALID_COORDINATES = [
    (91.0, 3.0),
    (-91.0, 3.0),
    (40.0, 181.0),
    (40.0, -181.0),
    (math.nextafter(90.0, math.inf), 0.0),
    (math.nextafter(-90.0, -math.inf), 0.0),
    (0.0, math.nextafter(180.0, math.inf)),
    (0.0, math.nextafter(-180.0, -math.inf)),
    (math.nan, 3.0),
    (40.0, math.nan),
    (math.inf, 3.0),
    (40.0, -math.inf),
    (True, 3.0),
    (40.0, False),
    ("40", 3.0),
    (40.0, "3"),
    (10**400, 3.0),
    (40.0, -(10**400)),
    (Decimal("40"), 3.0),
    (None, 3.0),
]
COORDINATE_LIMITS = [(90.0, 0.0), (-90.0, 0.0), (0.0, 180.0), (0.0, -180.0)]
NESTED_RADII = [(500, 1000), (500, 2000), (1000, 2000)]


def cell_of(latitude, longitude, radius):
    east, north = _project(latitude, longitude)
    return math.floor(east / radius), math.floor(north / radius)


def assert_error_without_values(error, code):
    assert error.code == code
    assert str(error) == code
    assert error.__cause__ is None
    assert error.__context__ is None


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_result_is_the_centre_of_the_cell_that_contains_the_point(
    radius, sample_points
):
    for index, (latitude, longitude) in enumerate(sample_points):
        east, north = _project(latitude, longitude)
        expected = grid_cell_centre(east, north, radius)
        result = _project(*approximate_location(latitude, longitude, radius))
        assert math.dist(result, expected) < 1, f"punto {index}"


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_a_point_on_the_lower_left_border_belongs_to_the_upper_right_cell(radius):
    assert grid_cell_centre(4_000_000.0, 2_000_000.0, radius) == (
        4_000_000.0 + radius / 2,
        2_000_000.0 + radius / 2,
    )


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_a_point_just_below_the_border_belongs_to_the_previous_cell(radius):
    assert grid_cell_centre(3_999_999.999, 1_999_999.999, radius) == (
        4_000_000.0 - radius / 2,
        2_000_000.0 - radius / 2,
    )


def test_negative_coordinates_round_down_to_the_cell_below():
    assert grid_cell_centre(-0.1, -0.1, 500) == (-250.0, -250.0)


def test_a_valid_point_outside_the_coherence_box_gives_a_value():
    latitude, longitude = approximate_location(60.0, 20.0, 1000)
    assert math.isfinite(latitude)
    assert math.isfinite(longitude)


@pytest.mark.parametrize(("latitude", "longitude"), COORDINATE_LIMITS)
def test_the_coordinate_limits_are_included(latitude, longitude):
    result = approximate_location(latitude, longitude, 1000)
    assert all(math.isfinite(value) for value in result)


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_same_point_and_radius_give_the_same_result(radius, sample_points):
    for latitude, longitude in sample_points:
        assert approximate_location(latitude, longitude, radius) == (
            approximate_location(latitude, longitude, radius)
        )


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_result_is_within_071_radius_of_the_point_in_the_projection(
    radius, sample_points
):
    for index, (latitude, longitude) in enumerate(sample_points):
        result = _project(*approximate_location(latitude, longitude, radius))
        assert math.dist(_project(latitude, longitude), result) <= 0.71 * radius, (
            f"punto {index}"
        )


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_two_points_of_the_same_cell_give_the_same_result(radius, sample_points):
    for index, (latitude, longitude) in enumerate(sample_points):
        east, north = _project(latitude, longitude)
        centre_east, centre_north = grid_cell_centre(east, north, radius)
        near_lower_left = _unproject(
            centre_east - radius / 2 + 1, centre_north - radius / 2 + 1
        )
        near_upper_right = _unproject(
            centre_east + radius / 2 - 1, centre_north + radius / 2 - 1
        )
        expected = approximate_location(latitude, longitude, radius)
        assert approximate_location(*near_lower_left, radius) == expected, (
            f"punto {index}"
        )
        assert approximate_location(*near_upper_right, radius) == expected, (
            f"punto {index}"
        )


@pytest.mark.parametrize("radius", PRIVACY_RADII)
def test_applying_the_function_to_its_result_gives_the_same_result(
    radius, sample_points
):
    for index, (latitude, longitude) in enumerate(sample_points):
        result = approximate_location(latitude, longitude, radius)
        assert approximate_location(*result, radius) == result, f"punto {index}"


@pytest.mark.parametrize(("fine", "coarse"), NESTED_RADII)
def test_the_fine_result_is_in_the_same_coarse_cell_as_the_point(
    fine, coarse, sample_points
):
    for index, (latitude, longitude) in enumerate(sample_points):
        result = approximate_location(latitude, longitude, fine)
        assert cell_of(*result, coarse) == cell_of(latitude, longitude, coarse), (
            f"punto {index}"
        )


@pytest.mark.parametrize("radius", INVALID_RADII)
def test_an_invalid_radius_fails_without_a_value(radius):
    with pytest.raises(ApproximationError) as caught:
        approximate_location(40.4168, -3.7038, radius)
    assert_error_without_values(caught.value, "radius_invalid")


@pytest.mark.parametrize(("latitude", "longitude"), INVALID_COORDINATES)
def test_an_invalid_coordinate_fails_without_a_value(latitude, longitude):
    with pytest.raises(ApproximationError) as caught:
        approximate_location(latitude, longitude, 1000)
    assert_error_without_values(caught.value, "coordinate_invalid")


def test_a_point_outside_the_projection_domain_fails_without_a_value():
    # El antípoda del origen de la proyección lanza GDALException de verdad
    with pytest.raises(ApproximationError) as caught:
        approximate_location(-52.0, -170.0, 1000)
    assert_error_without_values(caught.value, "projection_failed")


@pytest.mark.parametrize("stage", ["_project", "_unproject"])
def test_a_non_finite_projection_fails_without_a_value(stage, monkeypatch):
    monkeypatch.setattr(location, stage, lambda first, second: (math.inf, 0.0))
    with pytest.raises(ApproximationError) as caught:
        approximate_location(40.4168, -3.7038, 1000)
    assert_error_without_values(caught.value, "projection_failed")
