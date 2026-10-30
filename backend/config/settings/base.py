"""Settings comunes a todos los entornos. No lee el entorno: eso es cosa de env.py."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.gis",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.users",
    "apps.categories",
    "apps.assets",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# La cookie CSRF debe poder leerla el frontend; la de sesión, no
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_CONTENT_NEGOTIATION_CLASS": "apps.core.api.JSONOnlyNegotiation",
    "URL_FORMAT_OVERRIDE": None,
    "DEFAULT_VERSIONING_CLASS": None,
    # Sin autenticación por defecto y denegar por defecto: cada vista declara lo suyo
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": [],
    # Sin proxy de confianza: la IP del límite es siempre REMOTE_ADDR
    "NUM_PROXIES": 0,
    "EXCEPTION_HANDLER": "apps.core.api.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "VERSION": "1.0.0",
}

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "es"
USE_I18N = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# El SQL lleva email y hash como valores: se fija en INFO para que no salga al log
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {"django.db.backends": {"level": "INFO"}},
}


def build_database(name: str, user: str, password: str, host: str, port: int) -> dict:
    return {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": name,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": port,
            "CONN_MAX_AGE": 0,
            "OPTIONS": {"connect_timeout": 5},
        }
    }
