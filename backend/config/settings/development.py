from config.env import parse_bool, parse_port, read_optional, require
from config.settings.base import *  # noqa: F403
from config.settings.base import build_database

_env = require(
    None,
    (
        "DJANGO_SECRET_KEY",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ),
)

SECRET_KEY = _env["DJANGO_SECRET_KEY"]
DEBUG = parse_bool("DJANGO_DEBUG", read_optional(None, "DJANGO_DEBUG"))
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

DATABASES = build_database(
    name=_env["DB_NAME"],
    user=_env["DB_USER"],
    password=_env["DB_PASSWORD"],
    host=_env["DB_HOST"],
    port=parse_port("DB_PORT", _env["DB_PORT"]),
)
