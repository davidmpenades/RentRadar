import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Context, Decimal, Inexact, InvalidOperation, localcontext

REQUIRED = "required"
REPEATED = "repeated"
TOO_LONG = "too_long"
NOT_A_NUMBER = "not_a_number"
OUT_OF_RANGE = "out_of_range"
PARAMETER_CODES = frozenset({REQUIRED, REPEATED, TOO_LONG, NOT_A_NUMBER, OUT_OF_RANGE})

INVALID_PARAMETERS = "invalid_parameters"
ZONE_INVERTED = "zone_inverted"
ZONE_TOO_LARGE = "zone_too_large"

MAX_LENGTH = 32
MAX_AREA = Decimal(6)
LATITUDE_LIMIT = Decimal(90)
LONGITUDE_LIMIT = Decimal(180)
# [0-9] y no \d: \d acepta dígitos de otros alfabetos
DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
# Orden fijo: el de las claves del error
BOUND_LIMITS = (
    ("south", LATITUDE_LIMIT),
    ("west", LONGITUDE_LIMIT),
    ("north", LATITUDE_LIMIT),
    ("east", LONGITUDE_LIMIT),
)
# Con 100 dígitos el producto de dos operandos de 32 caracteres nunca se redondea
AREA_CONTEXT = Context(prec=100, traps=[Inexact, InvalidOperation])


@dataclass(frozen=True, slots=True)
class Zone:
    south: Decimal
    west: Decimal
    north: Decimal
    east: Decimal


@dataclass(frozen=True, slots=True)
class ZoneError:
    code: str
    params: dict[str, str]


def _text_error(values: list[str] | None) -> str | None:
    if not values:
        return REQUIRED
    if len(values) > 1:
        return REPEATED
    if len(values[0]) > MAX_LENGTH:
        return TOO_LONG
    if not DECIMAL_PATTERN.fullmatch(values[0]):
        return NOT_A_NUMBER
    return None


def _bound_error(values: list[str] | None, limit: Decimal) -> str | None:
    code = _text_error(values)
    if code is not None:
        return code
    # Comparar y no abs(): abs() redondea a la precisión del contexto global
    if not -limit <= Decimal(values[0]) <= limit:
        return OUT_OF_RANGE
    return None


def _is_inverted(zone: Zone) -> bool:
    return zone.south > zone.north or zone.west > zone.east


def _area(zone: Zone) -> Decimal:
    with localcontext(AREA_CONTEXT):
        return (zone.east - zone.west) * (zone.north - zone.south)


def parse_zone(params: Mapping[str, list[str]]) -> Zone | ZoneError:
    errors = {}
    for name, limit in BOUND_LIMITS:
        code = _bound_error(params.get(name), limit)
        if code is not None:
            errors[name] = code
    if errors:
        return ZoneError(INVALID_PARAMETERS, errors)

    south, west, north, east = (Decimal(params[name][0]) for name, _ in BOUND_LIMITS)
    zone = Zone(south=south, west=west, north=north, east=east)
    if _is_inverted(zone):
        return ZoneError(ZONE_INVERTED, {})
    if _area(zone) > MAX_AREA:
        return ZoneError(ZONE_TOO_LARGE, {})
    return zone
