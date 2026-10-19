from time import monotonic, sleep

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.core.db_wait import wait_until_available

FAILURE_MESSAGE = (
    "La base de datos no estuvo disponible en 60 segundos."
    " El arranque falla por la base de datos, no por la aplicación."
)


class Command(BaseCommand):
    help = "Espera hasta 60 segundos a que la base de datos acepte conexiones."

    def handle(self, *args, **options):
        available = wait_until_available(connection.ensure_connection, monotonic, sleep)
        if not available:
            raise CommandError(FAILURE_MESSAGE)
