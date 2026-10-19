"""Settings comunes a todos los entornos. No lee el entorno: eso es cosa de env.py."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = False

INSTALLED_APPS = [
    "django.contrib.gis",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "es"
USE_I18N = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


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
