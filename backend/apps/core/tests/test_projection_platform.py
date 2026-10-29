import logging
import math
from ctypes import byref, c_int

import pytest
from django.contrib.gis.gdal import (
    AxisOrder,
    CoordTransform,
    GDALException,
    SpatialReference,
    gdal_version,
)
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.geos import Point

GEOGRAPHIC_SRID = 4326
GRID_SRID = 3035

# (latitud, longitud, este, norte) en EPSG:3035, calculados una vez con esta imagen
REFERENCE_POINTS = {
    "madrid": (40.4168, -3.7038, 3159390.356, 2029850.920),
    "las_palmas": (28.1235, -15.4363, 1816110.911, 984556.390),
    "palma": (39.5696, 2.6502, 3686979.431, 1861579.356),
}

# Constantes de ETRS89-LAEA (GRS80, origen 52 N 10 E) de la guía EPSG 7-2
SEMI_MAJOR_AXIS = 6378137.0
INVERSE_FLATTENING = 298.257222101
ORIGIN_LATITUDE = math.radians(52)
ORIGIN_LONGITUDE = math.radians(10)
FALSE_EASTING = 4321000.0
FALSE_NORTHING = 3210000.0
ECCENTRICITY_SQUARED = 2 / INVERSE_FLATTENING - 1 / INVERSE_FLATTENING**2
ECCENTRICITY = math.sqrt(ECCENTRICITY_SQUARED)


def authalic_q(latitude):
    sine = math.sin(latitude)
    return (1 - ECCENTRICITY_SQUARED) * (
        sine / (1 - ECCENTRICITY_SQUARED * sine**2)
        - math.log((1 - ECCENTRICITY * sine) / (1 + ECCENTRICITY * sine))
        / (2 * ECCENTRICITY)
    )


Q_POLE = authalic_q(math.pi / 2)
ORIGIN_BETA = math.asin(authalic_q(ORIGIN_LATITUDE) / Q_POLE)
AUTHALIC_RADIUS = SEMI_MAJOR_AXIS * math.sqrt(Q_POLE / 2)
SCALE_D = (
    SEMI_MAJOR_AXIS
    * math.cos(ORIGIN_LATITUDE)
    / math.sqrt(1 - ECCENTRICITY_SQUARED * math.sin(ORIGIN_LATITUDE) ** 2)
    / (AUTHALIC_RADIUS * math.cos(ORIGIN_BETA))
)


def laea_europe(latitude, longitude):
    # Fórmula elipsoidal de la guía EPSG 7-2 escrita aquí, sin GDAL ni PROJ
    phi = math.radians(latitude)
    delta = math.radians(longitude) - ORIGIN_LONGITUDE
    beta = math.asin(authalic_q(phi) / Q_POLE)
    cos_cross = math.cos(ORIGIN_BETA) * math.cos(beta) * math.cos(delta)
    scale_b = AUTHALIC_RADIUS * math.sqrt(
        2 / (1 + math.sin(ORIGIN_BETA) * math.sin(beta) + cos_cross)
    )
    easting = FALSE_EASTING + scale_b * SCALE_D * math.cos(beta) * math.sin(delta)
    northing = FALSE_NORTHING + (scale_b / SCALE_D) * (
        math.cos(ORIGIN_BETA) * math.sin(beta)
        - math.sin(ORIGIN_BETA) * math.cos(beta) * math.cos(delta)
    )
    return easting, northing


def transform(x, y, source_srid, target_srid, axis_order=AxisOrder.TRADITIONAL):
    coord_transform = CoordTransform(
        SpatialReference(source_srid, axis_order=axis_order),
        SpatialReference(target_srid, axis_order=axis_order),
    )
    point = Point(x, y, srid=source_srid).transform(coord_transform, clone=True)
    return point.x, point.y


def proj_version():
    major, minor, patch = c_int(), c_int(), c_int()
    lgdal.OSRGetPROJVersion(byref(major), byref(minor), byref(patch))
    return major.value, minor.value, patch.value


def test_gdal_and_proj_versions_are_the_ones_of_the_image():
    assert gdal_version() == b"3.10.3"
    assert proj_version() == (9, 6, 0)


@pytest.mark.parametrize("name", REFERENCE_POINTS)
def test_traditional_axis_order_gives_easting_then_northing(name):
    latitude, longitude, easting, northing = REFERENCE_POINTS[name]
    projected = transform(longitude, latitude, GEOGRAPHIC_SRID, GRID_SRID)
    assert projected == pytest.approx((easting, northing), abs=1e-3)


def test_authority_axis_order_swaps_both_axes():
    latitude, longitude, easting, northing = REFERENCE_POINTS["madrid"]
    projected = transform(
        latitude, longitude, GEOGRAPHIC_SRID, GRID_SRID, AxisOrder.AUTHORITY
    )
    assert projected == pytest.approx((northing, easting), abs=1e-3)


def test_laea_formula_reproduces_the_published_epsg_example():
    # Ejemplo de la guía EPSG 7-2 para ETRS89-LAEA: 50 N 5 E
    assert laea_europe(50, 5) == pytest.approx((3962799.45, 2999718.85), abs=0.005)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        *[(lat, lon) for lat, lon, _, _ in REFERENCE_POINTS.values()],
        (43.5322, -5.6611),
        (36.834, -2.4637),
        (38.9067, 1.4206),
        (43.79, -9.30),
        (35.99, -5.61),
        (41.8, 3.2),
        (28.68, -17.76),
        (27.74, -18.16),
    ],
)
def test_proj_matches_the_laea_formula_within_one_millimetre(latitude, longitude):
    projected = transform(longitude, latitude, GEOGRAPHIC_SRID, GRID_SRID)
    assert projected == pytest.approx(laea_europe(latitude, longitude), abs=1e-3)


@pytest.mark.parametrize(
    ("latitude", "longitude"), [(-52, -170), (-52, 190), (-52.0000001, -170)]
)
def test_projecting_the_antipode_raises_gdal_exception_with_a_fixed_log(
    caplog, latitude, longitude
):
    with (
        caplog.at_level(logging.ERROR, logger="django.contrib.gis"),
        pytest.raises(GDALException) as caught,
    ):
        transform(longitude, latitude, GEOGRAPHIC_SRID, GRID_SRID)
    assert str(caught.value) == "OGR failure."
    assert [record.getMessage() for record in caplog.records] == [
        "GDAL_ERROR 1: b'Point outside of projection domain'"
    ]


@pytest.mark.parametrize(
    ("latitude", "longitude"), [(-51.999, -170), (-52, -169.99), (-60, -170)]
)
def test_projecting_next_to_the_antipode_gives_finite_values(latitude, longitude):
    projected = transform(longitude, latitude, GEOGRAPHIC_SRID, GRID_SRID)
    assert all(math.isfinite(value) for value in projected)


def test_unprojecting_outside_the_domain_raises_gdal_exception_with_a_fixed_log(
    caplog,
):
    with (
        caplog.at_level(logging.ERROR, logger="django.contrib.gis"),
        pytest.raises(GDALException),
    ):
        transform(-10_000_000.0, 0.0, GRID_SRID, GEOGRAPHIC_SRID)
    assert [record.getMessage() for record in caplog.records] == [
        "GDAL_ERROR 1: b'Point outside of projection domain'"
    ]
