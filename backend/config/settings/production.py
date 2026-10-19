from config.env import load_production_config, parse_bool, read_optional
from config.settings.base import *  # noqa: F403
from config.settings.base import build_database

_config = load_production_config()

# Se valida DJANGO_DEBUG para que un valor mal formado falle también aquí,
# pero se descarta: en producción la depuración siempre está apagada.
parse_bool("DJANGO_DEBUG", read_optional(None, "DJANGO_DEBUG"))
DEBUG = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECRET_KEY = _config.secret_key
ALLOWED_HOSTS = list(_config.allowed_hosts)

DATABASES = build_database(
    name=_config.db_name,
    user=_config.db_user,
    password=_config.db_password,
    host=_config.db_host,
    port=_config.db_port,
)
