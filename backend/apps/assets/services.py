from datetime import UTC, datetime

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import NON_FIELD_ERRORS

from apps.assets.location import ApproximationError, approximate_location
from apps.assets.models import Asset, AssetStatus
from apps.assets.rules import (
    CURRENCY,
    STATUSES_ON_CREATE,
    STATUSES_ON_UPDATE,
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
        "asset_not_found",
        "location_locked",
        "privacy_radius_locked",
    }
)

# Campo del servicio -> atributo del modelo, cuando no se llaman igual
ATTRIBUTES = {"category": "category_id", "location": "exact_location"}

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
        owner_id=owner_id,
        category_id=category_id,
        title=title,
        description=description,
        price=price,
        currency=currency,
        price_unit=price_unit,
        latitude=latitude,
        longitude=longitude,
        privacy_radius=privacy_radius,
        status=status,
    )
    if errors:
        raise DomainValidationError(errors)
    asset, errors = run_guarded(
        lambda: _insert(values=values, moment=moment), CONSTRAINT_CODES
    )
    if errors:
        raise DomainValidationError(errors)
    return asset


# Modifica solo los campos indicados; la pública se deriva si cambian exacta o radio
def update_asset(
    *,
    now,
    asset_id,
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
    asset_id, values, errors = _clean_for_update(
        asset_id=asset_id,
        category_id=category_id,
        title=title,
        description=description,
        price=price,
        currency=currency,
        price_unit=price_unit,
        latitude=latitude,
        longitude=longitude,
        privacy_radius=privacy_radius,
        status=status,
    )
    if errors:
        raise DomainValidationError(errors)
    asset, errors = run_guarded(
        lambda: _apply_update(asset_id=asset_id, values=values, moment=moment),
        CONSTRAINT_CODES,
    )
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
    *,
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
            field="owner",
            raw=owner_id,
            clean=lambda raw: clean_reference(raw, "owner"),
        ),
        "category": _required(
            field="category",
            raw=category_id,
            clean=lambda raw: clean_reference(raw, "category"),
        ),
        "title": _required(field="title", raw=title, clean=clean_title),
        "description": _required(
            field="description", raw=description, clean=clean_description
        ),
        "price": _required(field="price", raw=price, clean=clean_price),
        "price_unit": _required(
            field="price_unit", raw=price_unit, clean=clean_price_unit
        ),
        "currency": clean_currency(_default(raw=currency, default=CURRENCY)),
        "privacy_radius": clean_privacy_radius(
            _default(raw=privacy_radius, default=DEFAULT_PRIVACY_RADIUS)
        ),
        "status": clean_status(
            _default(raw=status, default=DEFAULT_STATUS), allowed=STATUSES_ON_CREATE
        ),
        "location": _clean_coordinates(latitude=latitude, longitude=longitude),
    }
    values = {field: value for field, (value, _) in results.items()}
    errors = {field: codes for field, (_, codes) in results.items() if codes}
    return values, errors


# Un campo obligatorio: no indicado o None es «required»; si no, lo valida su regla
def _required(*, field, raw, clean):
    if raw is _UNSET or raw is None:
        return None, [f"{field}_required"]
    return clean(raw)


# El valor por defecto solo vale si no se indicó nada; None cuenta como indicado
def _default(*, raw, default):
    return default if raw is _UNSET else raw


# Las dos coordenadas juntas: si falta alguna es «required»
def _clean_coordinates(*, latitude, longitude):
    if any(value is _UNSET or value is None for value in (latitude, longitude)):
        return None, ["location_required"]
    return clean_location(latitude, longitude)


# Dentro de la transacción: existencia, ubicación pública y guardado
def _insert(*, values, moment):
    missing = _missing_references(
        owner_id=values["owner"], category_id=values["category"]
    )
    if missing:
        raise DomainValidationError(missing)
    latitude, longitude = values["location"]
    public_location = _public_location(
        latitude=latitude, longitude=longitude, radius=values["privacy_radius"]
    )
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
        exact_location=Point(x=longitude, y=latitude, srid=4326),
        public_location=public_location,
        created_at=moment,
        updated_at=moment,
    )
    asset.save()
    return asset


# Los campos cuya referencia no existe, con su código
def _missing_references(*, owner_id, category_id):
    missing = {}
    if not get_user_model().objects.filter(pk=owner_id).exists():
        missing["owner"] = ["owner_not_found"]
    if not Category.objects.filter(pk=category_id).exists():
        missing["category"] = ["category_not_found"]
    return missing


# La ubicación pública, o None si la función de aproximación falla
def _public_location(*, latitude, longitude, radius):
    try:
        public_latitude, public_longitude = approximate_location(
            latitude, longitude, radius
        )
    except ApproximationError:
        return None
    return Point(x=public_longitude, y=public_latitude, srid=4326)


# Limpia solo lo indicado, todo a la vez: los errores de forma se devuelven juntos
def _clean_for_update(
    *,
    asset_id,
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
    required = {
        "category": (category_id, lambda raw: clean_reference(raw, "category")),
        "title": (title, clean_title),
        "description": (description, clean_description),
        "price": (price, clean_price),
        "price_unit": (price_unit, clean_price_unit),
    }
    # Aquí None no es «required» sino inválido, como al crear
    direct = {
        "currency": (currency, clean_currency),
        "privacy_radius": (privacy_radius, clean_privacy_radius),
        "status": (status, lambda raw: clean_status(raw, allowed=STATUSES_ON_UPDATE)),
    }
    results = {
        field: _required(field=field, raw=raw, clean=clean)
        for field, (raw, clean) in required.items()
        if raw is not _UNSET
    }
    results |= {
        field: clean(raw) for field, (raw, clean) in direct.items() if raw is not _UNSET
    }
    if latitude is not _UNSET or longitude is not _UNSET:
        results["location"] = _clean_coordinates(latitude=latitude, longitude=longitude)
    asset_id, asset_codes = clean_reference(asset_id, "asset")
    values = {field: value for field, (value, _) in results.items()}
    errors = {field: codes for field, (_, codes) in results.items() if codes}
    if asset_codes:
        errors["asset"] = asset_codes
    return asset_id, values, errors


# Dentro de la transacción: bloqueo, cambios, reglas de la BD y guardado
def _apply_update(*, asset_id, values, moment):
    # Es la primera lectura del bien: todo se compara con la fila ya bloqueada
    asset = Asset.objects.select_for_update().filter(pk=asset_id).first()
    if asset is None:
        raise DomainValidationError({"asset": ["asset_not_found"]})
    changes = _changed_values(asset=asset, values=values)
    errors = _update_errors(asset=asset, values=values, changes=changes)
    if errors:
        raise DomainValidationError(errors)
    if not changes:
        return asset
    for field, value in changes.items():
        setattr(asset, ATTRIBUTES.get(field, field), _model_value(field, value))
    update_fields = [ATTRIBUTES.get(field, field) for field in changes]
    if "location" in changes or "privacy_radius" in changes:
        public_location = _public_location(
            latitude=asset.exact_location.y,
            longitude=asset.exact_location.x,
            radius=asset.privacy_radius,
        )
        if public_location is None:
            raise DomainValidationError({NON_FIELD_ERRORS: [APPROXIMATION_FAILED]})
        asset.public_location = public_location
        update_fields.append("public_location")
    asset.updated_at = moment
    asset.save(update_fields=[*update_fields, "updated_at"])
    return asset


# Los valores indicados que difieren, con igualdad exacta, de los de la fila
def _changed_values(*, asset, values):
    stored = {
        "category": asset.category_id,
        "title": asset.title,
        "description": asset.description,
        "price": asset.price,
        "currency": asset.currency,
        "price_unit": asset.price_unit,
        "privacy_radius": asset.privacy_radius,
        "status": asset.status,
        "location": (asset.exact_location.y, asset.exact_location.x),
    }
    return {field: value for field, value in values.items() if value != stored[field]}


# Errores que exigen la fila: categoría inexistente y ubicación bloqueada
def _update_errors(*, asset, values, changes):
    errors = {}
    if (
        "category" in changes
        and not Category.objects.filter(pk=values["category"]).exists()
    ):
        errors["category"] = ["category_not_found"]
    # Bloquea si el bien está activo antes o va a estarlo después de la modificación
    resulting_status = values.get("status", asset.status)
    if AssetStatus.ACTIVE.value in (asset.status, resulting_status):
        if "location" in changes:
            errors["location"] = ["location_locked"]
        if "privacy_radius" in changes:
            errors["privacy_radius"] = ["privacy_radius_locked"]
    return errors


# La ubicación llega como (latitud, longitud) y el modelo la guarda como punto
def _model_value(field, value):
    if field != "location":
        return value
    latitude, longitude = value
    return Point(x=longitude, y=latitude, srid=4326)
