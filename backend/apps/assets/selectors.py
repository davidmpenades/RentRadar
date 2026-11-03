from django.contrib.gis.db.models import GeometryField
from django.db.models import FloatField, Func
from django.db.models.functions import Cast

from apps.assets.models import Asset
from apps.assets.zone import Zone

# Lista blanca: nunca se pide la ubicación exacta ni el id interno
PUBLIC_FIELDS = (
    "public_id",
    "title",
    "category__slug",
    "category__name",
    "price",
    "currency",
    "price_unit",
    "privacy_radius",
    "latitude",
    "longitude",
)


def visible_assets_in_zone(*, zone: Zone, limit: int) -> tuple[list[dict], bool]:
    # Mismo cast a geometry que el CHECK del modelo, para comparar en grados
    geometry = Cast("public_location", GeometryField())
    queryset = (
        Asset.objects.filter(status="active", owner__is_active=True)
        .annotate(
            longitude=Func(geometry, function="ST_X", output_field=FloatField()),
            latitude=Func(geometry, function="ST_Y", output_field=FloatField()),
        )
        .filter(
            longitude__range=(zone.west, zone.east),
            latitude__range=(zone.south, zone.north),
        )
        .order_by("-created_at", "-id")
        .values(*PUBLIC_FIELDS)
    )
    # Una fila de más indica que quedan bienes sin devolver, sin contar
    rows = list(queryset[: limit + 1])
    return rows[:limit], len(rows) > limit
