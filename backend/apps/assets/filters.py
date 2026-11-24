import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

from apps.assets.folding import fold_for_search
from apps.assets.zone import (
    INVALID_PARAMETERS,
    REPEATED,
    TOO_LONG,
    Zone,
    ZoneError,
    parse_zone,
)

EMPTY = "empty"
INVALID_FORMAT = "invalid_format"
CONTROL_CHAR = "control_char"

CATEGORY_MAX_LENGTH = 50
TEXT_MAX_LENGTH = 64
# Copia del patrón de categorías: este módulo no importa Django ni otras apps
CATEGORY_PATTERN = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")


@dataclass(frozen=True, slots=True)
class Filters:
    category_slug: str | None
    title_fragment: str | None


@dataclass(frozen=True, slots=True)
class PublicQuery:
    zone: Zone
    filters: Filters


# Valor por defecto compartido del selector: por eso Filters es inmutable
NO_FILTERS = Filters(category_slug=None, title_fragment=None)


def _clean_text(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _has_control_character(text: str) -> bool:
    return any(unicodedata.category(char) == "Cc" for char in text)


def _category_error(values: list[str]) -> str | None:
    if len(values) > 1:
        return REPEATED
    if not values[0]:
        return EMPTY
    if len(values[0]) > CATEGORY_MAX_LENGTH:
        return TOO_LONG
    if not CATEGORY_PATTERN.fullmatch(values[0]):
        return INVALID_FORMAT
    return None


def _text_error(values: list[str]) -> str | None:
    if len(values) > 1:
        return REPEATED
    text = _clean_text(values[0])
    if not text:
        return EMPTY
    if len(text) > TEXT_MAX_LENGTH:
        return TOO_LONG
    if _has_control_character(text):
        return CONTROL_CHAR
    return None


def parse_filters(params: Mapping[str, list[str]]) -> Filters | dict[str, str]:
    categories = params.get("category")
    texts = params.get("q")
    errors = {}
    if categories and (code := _category_error(categories)):
        errors["category"] = code
    if texts and (code := _text_error(texts)):
        errors["q"] = code
    if errors:
        return errors

    return Filters(
        category_slug=categories[0] if categories else None,
        title_fragment=fold_for_search(_clean_text(texts[0])) if texts else None,
    )


def parse_public_query(params: Mapping[str, list[str]]) -> PublicQuery | ZoneError:
    zone = parse_zone(params)
    filters = parse_filters(params)
    if isinstance(filters, dict):
        # La zona invertida o demasiado grande solo se avisa con los filtros bien
        zone_errors = {}
        if isinstance(zone, ZoneError) and zone.code == INVALID_PARAMETERS:
            zone_errors = zone.params
        return ZoneError(INVALID_PARAMETERS, {**zone_errors, **filters})
    if isinstance(zone, ZoneError):
        return zone
    return PublicQuery(zone=zone, filters=filters)
