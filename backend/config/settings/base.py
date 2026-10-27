"""Settings comunes a todos los entornos. No lee el entorno: eso es cosa de env.py."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.gis",
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
