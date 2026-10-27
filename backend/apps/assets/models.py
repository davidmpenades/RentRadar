from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.db.models.functions import IsEmpty
from django.db import models
from django.db.models import FloatField, Func, Q
from django.db.models.functions import Cast, Length
from django.db.models.lookups import Range

from apps.assets.location import LATITUDE_LIMITS, LONGITUDE_LIMITS, PRIVACY_RADII
from apps.assets.rules import (
    CURRENCY,
    DESCRIPTION_MAXIMUM,
    DESCRIPTION_MINIMUM,
    PRICE_MAXIMUM,
    PRICE_MINIMUM,
    TITLE_MAXIMUM,
    TITLE_MINIMUM_VISIBLE,
)


class AssetStatus(models.TextChoices):
    ACTIVE = "active"
    PAUSED = "paused"


class PriceUnit(models.TextChoices):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# Ubicación no vacía y finita: geography ajusta el rango pero guarda NaN
def _valid_location(field_name):
    geometry = Cast(field_name, GeometryField())
    return Q(
        ~Q(IsEmpty(geometry)),
        Range(
            Func(geometry, function="ST_X", output_field=FloatField()),
            LONGITUDE_LIMITS,
        ),
        Range(
            Func(geometry, function="ST_Y", output_field=FloatField()),
            LATITUDE_LIMITS,
        ),
    )


class Asset(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    category = models.ForeignKey(
        "categories.Category", on_delete=models.PROTECT, related_name="+"
    )
    title = models.TextField()
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.TextField()
    price_unit = models.TextField(choices=PriceUnit.choices)
    exact_location = gis_models.PointField(
        geography=True, srid=4326, spatial_index=False
    )
    public_location = gis_models.PointField(geography=True, srid=4326)
    privacy_radius = models.IntegerField()
    status = models.TextField(choices=AssetStatus.choices)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        constraints = [
            # En la BD el mínimo cuenta puntos de código, no caracteres visibles
            models.CheckConstraint(
                condition=Q(
                    Range(Length("title"), (TITLE_MINIMUM_VISIBLE, TITLE_MAXIMUM))
                ),
                name="assets_asset_title_length",
            ),
            models.CheckConstraint(
                condition=Q(
                    Range(
                        Length("description"),
                        (DESCRIPTION_MINIMUM, DESCRIPTION_MAXIMUM),
                    )
                ),
                name="assets_asset_description_length",
            ),
            models.CheckConstraint(
                condition=Q(price__range=(PRICE_MINIMUM, PRICE_MAXIMUM)),
                name="assets_asset_price_range",
            ),
            models.CheckConstraint(
                condition=Q(currency=CURRENCY), name="assets_asset_currency_eur"
            ),
            models.CheckConstraint(
                condition=Q(price_unit__in=PriceUnit.values),
                name="assets_asset_price_unit_valid",
            ),
            models.CheckConstraint(
                condition=Q(privacy_radius__in=PRIVACY_RADII),
                name="assets_asset_privacy_radius_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=AssetStatus.values),
                name="assets_asset_status_valid",
            ),
            models.CheckConstraint(
                condition=_valid_location("exact_location"),
                name="assets_asset_exact_location_valid",
            ),
            models.CheckConstraint(
                condition=_valid_location("public_location"),
                name="assets_asset_public_location_valid",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.pk})"
