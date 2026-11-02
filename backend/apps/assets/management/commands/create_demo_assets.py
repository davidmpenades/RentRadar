import secrets
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.demo import DEMO_ASSETS, DEMO_EMAIL
from apps.assets.services import create_asset, update_asset
from apps.categories.models import Category
from apps.users.services import create_user

# Tupla y no conjunto: un valor no hashable no debe lanzar TypeError
ALLOWED_ENVIRONMENTS = ("development", "test")
ENVIRONMENT_MESSAGE = (
    "El comando de demostración solo se ejecuta en development o test."
)
EXISTING_MESSAGE = "El propietario de demostración ya existe; no se ha creado nada."


class Command(BaseCommand):
    help = "Crea un propietario de demostración y sus bienes en la base de datos."

    # La contraseña y la hora entran por métodos para poder sustituirlas en los tests
    def generate_password(self):
        return secrets.token_urlsafe(32)

    def current_time(self):
        return datetime.now(UTC)

    def handle(self, *args, **options):
        # Primera sentencia: sin entorno permitido no se toca la base de datos
        if getattr(settings, "ENVIRONMENT", None) not in ALLOWED_ENVIRONMENTS:
            raise CommandError(ENVIRONMENT_MESSAGE)
        with transaction.atomic():
            if get_user_model().objects.filter(email=DEMO_EMAIL).exists():
                self.stdout.write(EXISTING_MESSAGE)
                return
            owner = create_user(email=DEMO_EMAIL, password=self.generate_password())
            self._create_assets(owner_id=owner.pk, now=self.current_time())
        self.stdout.write(_created_message())

    def _create_assets(self, *, owner_id, now):
        category_ids = dict(Category.objects.values_list("slug", "pk"))
        for index, demo in enumerate(DEMO_ASSETS):
            # Cada bien un minuto más antiguo que el anterior, para un orden estable
            moment = now - timedelta(minutes=index)
            asset = create_asset(
                now=moment,
                owner_id=owner_id,
                category_id=category_ids[demo.category_slug],
                title=demo.title,
                description=demo.description,
                price=demo.price,
                price_unit=demo.price_unit,
                privacy_radius=demo.privacy_radius,
                latitude=demo.latitude,
                longitude=demo.longitude,
            )
            if demo.active:
                update_asset(now=moment, asset_id=asset.pk, status="active")


def _created_message():
    active = sum(demo.active for demo in DEMO_ASSETS)
    paused = len(DEMO_ASSETS) - active
    return (
        f"Creados {len(DEMO_ASSETS)} bienes de demostración "
        f"({active} activos, {paused} pausado)."
    )
