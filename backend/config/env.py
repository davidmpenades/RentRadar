"""Único lector del entorno. Ningún mensaje de error incluye el valor recibido."""

import ipaddress
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from django.core.exceptions import ImproperlyConfigured

KNOWN_VARIABLES = frozenset(
    {
        "DJANGO_ENV",
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    }
)
UNTRIMMED_VARIABLES = frozenset({"DJANGO_SECRET_KEY", "DB_PASSWORD"})
ENVIRONMENTS = ("development", "test", "production")
PRODUCTION_REQUIRED = (
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
)
MIN_SECRET_KEY_LENGTH = 50
INSECURE_MARKER = "insecure-"
TRUE_VALUES = frozenset({"true", "1"})
FALSE_VALUES = frozenset({"false", "0"})
DOMAIN_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


@dataclass(frozen=True)
class ProductionConfig:
    secret_key: str
    allowed_hosts: tuple[str, ...]
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str


def _read(environ: Mapping[str, str] | None, name: str) -> str:
    if name not in KNOWN_VARIABLES:
        raise ValueError(f"Variable no declarada en KNOWN_VARIABLES: {name}")
    source = os.environ if environ is None else environ
    value = source.get(name, "")
    if not value.strip():
        return ""
    # Los secretos se devuelven intactos: un espacio puede ser parte del valor
    return value if name in UNTRIMMED_VARIABLES else value.strip()


def resolve_settings_module(environ: Mapping[str, str] | None = None) -> str:
    env = _read(environ, "DJANGO_ENV")
    if env not in ENVIRONMENTS:
        raise ImproperlyConfigured(
            f"DJANGO_ENV debe ser uno de: {', '.join(ENVIRONMENTS)}."
        )
    return f"config.settings.{env}"


def require(environ: Mapping[str, str] | None, names: Iterable[str]) -> dict[str, str]:
    values = {name: _read(environ, name) for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ImproperlyConfigured(_missing_message(missing))
    return values


def parse_bool(name: str, raw: str | None) -> bool:
    value = (raw or "").strip().lower()
    if not value or value in FALSE_VALUES:
        return False
    if value in TRUE_VALUES:
        return True
    raise ImproperlyConfigured(f"{name} debe ser true, false, 1 o 0.")


def parse_port(name: str, raw: str) -> int:
    message = f"{name} debe ser un entero entre 1 y 65535."
    # int() aceptaría "8_0", "+80", espacios y dígitos no ASCII
    if not (raw.isascii() and raw.isdigit()):
        raise ImproperlyConfigured(message)
    port = int(raw)
    if not 1 <= port <= 65535:
        raise ImproperlyConfigured(message)
    return port


def parse_allowed_hosts(name: str, raw: str) -> list[str]:
    hosts = [host.strip() for host in raw.split(",") if host.strip()]
    if not all(_is_valid_host(host) for host in hosts):
        raise ImproperlyConfigured(
            f"{name} solo admite dominios, dominios con punto inicial o IP,"
            " separados por comas."
        )
    return hosts


def load_production_config(
    environ: Mapping[str, str] | None = None,
) -> ProductionConfig:
    values = {name: _read(environ, name) for name in PRODUCTION_REQUIRED}
    problems = []
    hosts: list[str] = []
    port = 0

    if values["DJANGO_ALLOWED_HOSTS"]:
        try:
            hosts = parse_allowed_hosts(
                "DJANGO_ALLOWED_HOSTS", values["DJANGO_ALLOWED_HOSTS"]
            )
        except ImproperlyConfigured as error:
            problems.append(str(error))
        else:
            # Una lista sin elementos tras quitar los vacíos cuenta como ausente
            if not hosts:
                values["DJANGO_ALLOWED_HOSTS"] = ""

    missing = [name for name, value in values.items() if not value]
    if missing:
        problems.insert(0, _missing_message(missing))

    if values["DB_PORT"]:
        try:
            port = parse_port("DB_PORT", values["DB_PORT"])
        except ImproperlyConfigured as error:
            problems.append(str(error))

    secret_key = values["DJANGO_SECRET_KEY"]
    if secret_key and len(secret_key) < MIN_SECRET_KEY_LENGTH:
        problems.append(
            f"DJANGO_SECRET_KEY debe tener al menos {MIN_SECRET_KEY_LENGTH} caracteres."
        )
    for name in ("DJANGO_SECRET_KEY", "DB_PASSWORD"):
        if INSECURE_MARKER in values[name]:
            problems.append(f"{name} no puede contener «{INSECURE_MARKER}».")

    if problems:
        raise ImproperlyConfigured(
            "Configuración de producción no válida:\n- " + "\n- ".join(problems)
        )
    return ProductionConfig(
        secret_key=secret_key,
        allowed_hosts=tuple(hosts),
        db_host=values["DB_HOST"],
        db_port=port,
        db_name=values["DB_NAME"],
        db_user=values["DB_USER"],
        db_password=values["DB_PASSWORD"],
    )


def _missing_message(missing: Iterable[str]) -> str:
    return f"Faltan variables obligatorias o están vacías: {', '.join(missing)}."


def _is_valid_host(host: str) -> bool:
    if host.startswith("[") and host.endswith("]"):
        return _is_ip(host[1:-1], version=6)
    if _is_ip(host, version=4):
        return True
    domain = host.removeprefix(".")
    return len(domain) <= 253 and all(
        DOMAIN_LABEL.match(label) for label in domain.split(".")
    )


def _is_ip(value: str, version: int) -> bool:
    try:
        return ipaddress.ip_address(value).version == version
    except ValueError:
        return False
