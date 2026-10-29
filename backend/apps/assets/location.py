import math

from django.contrib.gis.gdal import (
    AxisOrder,
    CoordTransform,
    GDALException,
    SpatialReference,
    SRSException,
)
from django.contrib.gis.geos import GEOSException, Point

PRIVACY_RADII = (500, 1000, 2000)
LATITUDE_LIMITS = (-90.0, 90.0)
LONGITUDE_LIMITS = (-180.0, 180.0)
GEOGRAPHIC_SRID = 4326
GRID_SRID = 3035
PUBLIC_DECIMALS = 6

RADIUS_INVALID = "radius_invalid"
COORDINATE_INVALID = "coordinate_invalid"
PROJECTION_FAILED = "projection_failed"


class ApproximationError(ValueError):
    # El mensaje es el propio código: nunca lleva coordenadas
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# Centro de la celda que contiene la coordenada, redondeado para publicarlo
def approximate_location(latitude, longitude, radius):
    if not _is_privacy_radius(radius):
        raise ApproximationError(RADIUS_INVALID)
    latitude = _valid_coordinate(latitude, LATITUDE_LIMITS)
    longitude = _valid_coordinate(longitude, LONGITUDE_LIMITS)
    if latitude is None or longitude is None:
        raise ApproximationError(COORDINATE_INVALID)
    projected = _transform_or_none(_project, latitude, longitude)
    if projected is None:
        raise ApproximationError(PROJECTION_FAILED)
    centre_easting, centre_northing = grid_cell_centre(*projected, radius)
    centre = _transform_or_none(_unproject, centre_easting, centre_northing)
    if centre is None:
        raise ApproximationError(PROJECTION_FAILED)
    return round(centre[0], PUBLIC_DECIMALS), round(centre[1], PUBLIC_DECIMALS)


def grid_cell_centre(easting, northing, radius):
    # floor deja en la celda su borde inferior e izquierdo
    return (
        (math.floor(easting / radius) + 0.5) * radius,
        (math.floor(northing / radius) + 0.5) * radius,
    )


def _is_privacy_radius(radius):
    return isinstance(radius, int) and radius in PRIVACY_RADII


# La coordenada como float si es un número finito dentro de sus límites; si no, None
def _valid_coordinate(value, limits):
    # bool hereda de int: sin esta exclusión True sería la coordenada 1
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    if not math.isfinite(number) or not limits[0] <= number <= limits[1]:
        return None
    return number


# Aplica la transformación y da None si falla o no da un valor finito
def _transform_or_none(transformation, first, second):
    try:
        result = transformation(first, second)
    except (GDALException, SRSException, GEOSException):
        return None
    return result if all(math.isfinite(value) for value in result) else None


def _project(latitude, longitude):
    return _transform(longitude, latitude, GEOGRAPHIC_SRID, GRID_SRID)


def _unproject(easting, northing):
    longitude, latitude = _transform(easting, northing, GRID_SRID, GEOGRAPHIC_SRID)
    return latitude, longitude


# Transforma un punto entre dos SRID con el orden de ejes x = longitud o este
def _transform(x, y, source_srid, target_srid):
    # Se crea en cada llamada porque los objetos de GDAL no son thread-safe
    coord_transform = CoordTransform(
        SpatialReference(source_srid, axis_order=AxisOrder.TRADITIONAL),
        SpatialReference(target_srid, axis_order=AxisOrder.TRADITIONAL),
    )
    point = Point(x, y, srid=source_srid).transform(coord_transform, clone=True)
    return point.x, point.y
