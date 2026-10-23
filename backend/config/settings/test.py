from config.env import parse_bool, parse_port, read_optional, require
from config.settings.base import *  # noqa: F403
from config.settings.base import build_database

TEST_DATABASE_NAME = "rentradar_test"

_env = require(None, ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD"))

# Clave fija solo en test: no es un secreto y producción la rechazaría
SECRET_KEY = "insecure-test-only-not-a-secret"

# Se valida DJANGO_DEBUG para que un valor mal formado falle también aquí,
# pero se descarta: en test la depuración siempre está apagada
parse_bool("DJANGO_DEBUG", read_optional(None, "DJANGO_DEBUG"))
DEBUG = False

# Hasher rápido solo en test: PBKDF2 tardaría segundos por usuario creado
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DATABASES = build_database(
    name=TEST_DATABASE_NAME,
    user=_env["DB_USER"],
    password=_env["DB_PASSWORD"],
    host=_env["DB_HOST"],
    port=parse_port("DB_PORT", _env["DB_PORT"]),
)
DATABASES["default"]["TEST"] = {"NAME": TEST_DATABASE_NAME}
