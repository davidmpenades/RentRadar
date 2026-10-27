from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import NON_FIELD_ERRORS

from apps.assets.location import ApproximationError, approximate_location
from apps.assets.models import Asset, AssetStatus
from apps.assets.rules import (
    CURRENCY,
    STATUSES_ON_CREATE,
    clean_currency,
    clean_description,
    clean_location,
    clean_price,
    clean_price_unit,
    clean_privacy_radius,
    clean_reference,
    clean_status,
    clean_title,
)
from apps.categories.models import Category
from apps.core.db import CONSTRAINT_VIOLATED, run_guarded
from apps.core.errors import DomainValidationError

_UNSET = object()
DEFAULT_PRIVACY_RADIUS = 1000
DEFAULT_STATUS = AssetStatus.PAUSED.value
APPROXIMATION_FAILED = "approximation_failed"

ERROR_CODES = frozenset(
    {
        "owner_required",
        "owner_invalid",
        "owner_not_found",
        "category_required",
        "category_invalid",
        "category_not_found",
        "title_required",
        "title_invalid",
        "title_too_short",
        "title_too_long",
        "title_control_char",
        "title_format_char",
        "description_required",
        "description_invalid",
        "description_too_short",
        "description_too_long",
        "description_control_char",
        "description_format_char",
        "price_required",
        "price_invalid",
        "price_out_of_range",
        "price_too_precise",
        "currency_invalid",
        "price_unit_required",
        "price_unit_invalid",
        "privacy_radius_invalid",
        "status_invalid",
        "location_required",
        "location_invalid",
        "location_out_of_range",
        "location_outside_bounds",
        APPROXIMATION_FAILED,
        CONSTRAINT_VIOLATED,
    }
)

# Restricción de la BD -> (campo, código); la de la ubicación pública no se traduce
CONSTRAINT_CODES = {
    "assets_asset_title_length": ("title", "title_invalid"),
    "assets_asset_description_length": ("description", "description_invalid"),
    "assets_asset_price_range": ("price", "price_out_of_range"),
    "assets_asset_currency_eur": ("currency", "currency_invalid"),
    "assets_asset_price_unit_valid": ("price_unit", "price_unit_invalid"),
    "assets_asset_privacy_radius_valid": ("privacy_radius", "privacy_radius_invalid"),
    "assets_asset_status_valid": ("status", "status_invalid"),
    "assets_asset_exact_location_valid": ("location", "location_invalid"),
    "assets_asset_owner_id_23c9aaf7_fk_users_user_id": ("owner", "owner_not_found"),
    "assets_asset_category_id_b30c6baf_fk_categories_category_id": (
        "category",
        "category_not_found",
    ),
}


# Crea un bien pausado con su ubicación pública derivada de la exacta
def create_asset(
    *,
    now,
    owner_id=_UNSET,
    category_id=_UNSET,
    title=_UNSET,
    description=_UNSET,
    price=_UNSET,
    currency=_UNSET,
    price_unit=_UNSET,
    latitude=_UNSET,
    longitude=_UNSET,
    privacy_radius=_UNSET,
    status=_UNSET,
):
    moment = _aware_utc(now)
    values, errors = _clean_for_creation(
        owner_id,
        category_id,
        title,
        description,
        price,
        currency,
        price_unit,
        latitude,
        longitude,
        privacy_radius,
        status,
    )
    if errors:
        raise DomainValidationError(errors)
    asset, errors = run_guarded(lambda: _insert(values, moment), CONSTRAINT_CODES)
    if errors:
        raise DomainValidationError(errors)
    return asset


# La hora recibida en UTC, o un error de programación si no tiene zona horaria
def _aware_utc(now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("now_not_aware")
    return now.astimezone(UTC)


# Limpia todos los campos a la vez: los errores de forma se devuelven juntos
def _clean_for_creation(
    owner_id,
    category_id,
    title,
    description,
    price,
    currency,
    price_unit,
    latitude,
    longitude,
    privacy_radius,
    status,
):
    results = {
        "owner": _required(
            "owner", owner_id, lambda raw: clean_reference(raw, "owner")
        ),
        "category": _required(
            "category", category_id, lambda raw: clean_reference(raw, "category")
        ),
        "title": _required("title", title, clean_title),
        "description": _required("description", description, clean_description),
        "price": _required("price", price, clean_price),
        "price_unit": _required("price_unit", price_unit, clean_price_unit),
        "currency": clean_currency(_default(currency, CURRENCY)),
        "privacy_radius": clean_privacy_radius(
            _default(privacy_radius, DEFAULT_PRIVACY_RADIUS)
        ),
        "status": clean_status(
            _default(status, DEFAULT_STATUS), allowed=STATUSES_ON_CREATE
        ),
        "location": _clean_coordinates(latitude, longitude),
    }
    values = {field: value for field, (value, _) in results.items()}
    errors = {field: codes for field, (_, codes) in results.items() if codes}
    return values, errors


# Un campo obligatorio: no indicado o None es «required»; si no, lo valida su regla
def _required(field, raw, clean):
    if raw is _UNSET or raw is None:
        return None, [f"{field}_required"]
    return clean(raw)


# El valor por defecto solo vale si no se indicó nada; None cuenta como indicado
def _default(raw, default):
    return default if raw is _UNSET else raw


# Las dos coordenadas juntas: si falta alguna es «required»
def _clean_coordinates(latitude, longitude):
    if any(value is _UNSET or value is None for value in (latitude, longitude)):
        return None, ["location_required"]
    return clean_location(latitude, longitude)


# Dentro de la transacción: existencia, ubicación pública y guardado
def _insert(values, moment):
    missing = _missing_references(values["owner"], values["category"])
    if missing:
        raise DomainValidationError(missing)
    latitude, longitude = values["location"]
    public_location = _public_location(latitude, longitude, values["privacy_radius"])
    if public_location is None:
        raise DomainValidationError({NON_FIELD_ERRORS: [APPROXIMATION_FAILED]})
    asset = Asset(
        owner_id=values["owner"],
        category_id=values["category"],
        title=values["title"],
        description=values["description"],
        price=values["price"],
        currency=values["currency"],
        price_unit=values["price_unit"],
        privacy_radius=values["privacy_radius"],
        status=values["status"],
        exact_location=Point(longitude, latitude, srid=4326),
        public_location=public_location,
        created_at=moment,
        updated_at=moment,
    )
    asset.save()
    return asset


# Los campos cuya referencia no existe, con su código
def _missing_references(owner_id, category_id):
    missing = {}
    if not get_user_model().objects.filter(pk=owner_id).exists():
        missing["owner"] = ["owner_not_found"]
    if not Category.objects.filter(pk=category_id).exists():
        missing["category"] = ["category_not_found"]
    return missing


# La ubicación pública, o None si la función de aproximación falla
def _public_location(latitude, longitude, radius):
    try:
        public_latitude, public_longitude = approximate_location(
            latitude, longitude, radius
        )
    except ApproximationError:
        return None
    return Point(public_longitude, public_latitude, srid=4326)
