import math
import re
import unicodedata
from decimal import Decimal

from apps.assets.location import LATITUDE_LIMITS, LONGITUDE_LIMITS, PRIVACY_RADII
from apps.core.text import contains_control_character

ZERO_WIDTH_JOINER = chr(0x200D)
DESCRIPTION_CONTROLS = "\n\r\t"
TITLE_MINIMUM_VISIBLE = 3
TITLE_MAXIMUM = 100
DESCRIPTION_MINIMUM = 20
DESCRIPTION_MAXIMUM = 2000

PRICE_PATTERN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
PRICE_MINIMUM = Decimal("0.01")
PRICE_MAXIMUM = Decimal("99999.99")
PRICE_DECIMALS = 2
PRICE_QUANTUM = Decimal(1).scaleb(-PRICE_DECIMALS)

CURRENCY = "EUR"
PRICE_UNITS = ("hour", "day", "week", "month")
STATUSES_ON_CREATE = ("paused",)
STATUSES_ON_UPDATE = ("active", "paused")

COHERENCE_LATITUDE = (27.5, 44.0)
COHERENCE_LONGITUDE = (-18.5, 5.0)

MAXIMUM_REFERENCE = 2**63 - 1
REFERENCE_INVALID_CODES = {
    "owner": "owner_invalid",
    "category": "category_invalid",
    "asset": "asset_not_found",
}


# Título recortado y en NFC, o los códigos que lo rechazan
def clean_title(raw):
    return _clean_text(
        raw,
        "title",
        minimum=TITLE_MINIMUM_VISIBLE,
        count_for_minimum=_visible_length,
        maximum=TITLE_MAXIMUM,
        allowed_controls="",
    )


# Descripción recortada y en NFC, o los códigos que la rechazan
def clean_description(raw):
    return _clean_text(
        raw,
        "description",
        minimum=DESCRIPTION_MINIMUM,
        count_for_minimum=len,
        maximum=DESCRIPTION_MAXIMUM,
        allowed_controls=DESCRIPTION_CONTROLS,
    )


# Precio como Decimal canónico de 2 decimales, o los códigos que lo rechazan
def clean_price(raw):
    if not isinstance(raw, (str, Decimal)):
        return None, ["price_invalid"]
    text = raw if isinstance(raw, str) else str(raw)
    if not PRICE_PATTERN.fullmatch(text):
        return None, ["price_invalid"]
    value = Decimal(text)
    codes = []
    if not PRICE_MINIMUM <= value <= PRICE_MAXIMUM:
        codes.append("price_out_of_range")
    # Los ceros finales no cuentan como decimales
    if len(text.partition(".")[2].rstrip("0")) > PRICE_DECIMALS:
        codes.append("price_too_precise")
    return (None, codes) if codes else (value.quantize(PRICE_QUANTUM), [])


# Moneda: solo EUR
def clean_currency(raw):
    return _clean_choice(raw, (CURRENCY,), "currency_invalid")


# Unidad de precio de la lista cerrada
def clean_price_unit(raw):
    return _clean_choice(raw, PRICE_UNITS, "price_unit_invalid")


# Radio de privacidad: entero de los admitidos
def clean_privacy_radius(raw):
    if not isinstance(raw, int):
        return None, ["privacy_radius_invalid"]
    return _clean_choice(raw, PRIVACY_RADII, "privacy_radius_invalid")


# Estado dentro de los que admite la operación (al crear y al modificar difieren)
def clean_status(raw, *, allowed):
    return _clean_choice(raw, allowed, "status_invalid")


# Latitud y longitud como floats, con un único código por precedencia
def clean_location(latitude, longitude):
    coordinates = [_coordinate_as_float(latitude), _coordinate_as_float(longitude)]
    if None in coordinates:
        return None, ["location_invalid"]
    latitude, longitude = coordinates
    in_range = _inside(latitude, LATITUDE_LIMITS) and _inside(
        longitude, LONGITUDE_LIMITS
    )
    if not in_range:
        return None, ["location_out_of_range"]
    in_box = _inside(latitude, COHERENCE_LATITUDE) and _inside(
        longitude, COHERENCE_LONGITUDE
    )
    if not in_box:
        return None, ["location_outside_bounds"]
    return (latitude, longitude), []


# Identificador de propietario, categoría o bien; su código de error depende del campo
def clean_reference(raw, field):
    valid = (
        isinstance(raw, int)
        and not isinstance(raw, bool)
        and 1 <= raw <= MAXIMUM_REFERENCE
    )
    return (raw, []) if valid else (None, [REFERENCE_INVALID_CODES[field]])


# Lo común a título y descripción: tipo, sustitutos, recorte, NFC y después los códigos
def _clean_text(raw, field, *, minimum, count_for_minimum, maximum, allowed_controls):
    if not isinstance(raw, str) or _has_lone_surrogate(raw):
        return None, [f"{field}_invalid"]
    text = unicodedata.normalize("NFC", raw.strip())
    codes = []
    if contains_control_character(_without(text, allowed_controls)):
        codes.append(f"{field}_control_char")
    if any(_is_format_character(char) for char in text):
        codes.append(f"{field}_format_char")
    if count_for_minimum(text) < minimum:
        codes.append(f"{field}_too_short")
    if len(text) > maximum:
        codes.append(f"{field}_too_long")
    return (None, codes) if codes else (text, [])


# Un sustituto suelto no es texto válido: psycopg lo rechazaría con un error crudo
def _has_lone_surrogate(text):
    return any(unicodedata.category(char) == "Cs" for char in text)


# Formato salvo la unión de ancho cero, que forma los emojis compuestos
def _is_format_character(char):
    return unicodedata.category(char) == "Cf" and char != ZERO_WIDTH_JOINER


# Caracteres que se ven: ni espacio, ni de control, ni de formato (la unión incluida)
def _visible_length(text):
    return sum(
        1
        for char in text
        if not char.isspace() and unicodedata.category(char) not in ("Cc", "Cf")
    )


# El texto sin los caracteres que se admiten aunque sean de control
def _without(text, allowed):
    return "".join(char for char in text if char not in allowed)


# El valor si está en la lista cerrada; si no, el código
def _clean_choice(raw, allowed, code):
    return (raw, []) if raw in allowed else (None, [code])


# La coordenada como float, o None si no es un número finito de un tipo admitido
def _coordinate_as_float(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


# Si el valor está dentro de los límites, ambos incluidos
def _inside(value, limits):
    return limits[0] <= value <= limits[1]
