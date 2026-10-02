import traceback

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import (
    load_production_config,
    parse_allowed_hosts,
    parse_bool,
    parse_port,
    require,
    resolve_settings_module,
)

PRODUCTION_REQUIRED = (
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
)
SECRET_SENTINEL = "SENTINEL-SECRET-" + "k" * 40
PASSWORD_SENTINEL = "SENTINEL-PASSWORD-7f3a"


def valid_production_environ(**overrides):
    environ = {
        "DJANGO_SECRET_KEY": SECRET_SENTINEL,
        "DJANGO_ALLOWED_HOSTS": "example.com",
        "DB_HOST": "SENTINEL-HOST",
        "DB_PORT": "5432",
        "DB_NAME": "SENTINEL-NAME",
        "DB_USER": "SENTINEL-USER",
        "DB_PASSWORD": PASSWORD_SENTINEL,
    }
    environ.update(overrides)
    return environ


def production_error(environ):
    with pytest.raises(ImproperlyConfigured) as excinfo:
        load_production_config(environ)
    return str(excinfo.value)


def assert_no_value_leaks(message, environ):
    for value in environ.values():
        if value.strip():
            assert value.strip() not in message


# RF-9 / RF-10: selección del módulo de settings


@pytest.mark.parametrize("env", ["development", "test", "production"])
def test_resolve_settings_module_maps_each_environment(env):
    assert resolve_settings_module({"DJANGO_ENV": env}) == f"config.settings.{env}"


def test_resolve_settings_module_strips_surrounding_spaces():
    assert resolve_settings_module({"DJANGO_ENV": " test "}) == "config.settings.test"


@pytest.mark.parametrize(
    "environ", [{}, {"DJANGO_ENV": "Production"}, {"DJANGO_ENV": "prod"}]
)
def test_resolve_settings_module_rejects_unknown_and_lists_valid_values(environ):
    with pytest.raises(ImproperlyConfigured) as excinfo:
        resolve_settings_module(environ)
    message = str(excinfo.value)
    assert "DJANGO_ENV" in message
    for valid in ("development", "test", "production"):
        assert valid in message
    assert "Production" not in message
    assert "prod," not in message


# Lector interno: solo variables declaradas


def test_require_rejects_undeclared_variable():
    with pytest.raises(ValueError, match="UNDECLARED_VAR"):
        require({"UNDECLARED_VAR": "x"}, ["UNDECLARED_VAR"])


def test_require_strips_values_and_treats_blank_as_missing():
    with pytest.raises(ImproperlyConfigured) as excinfo:
        require(
            {"DB_HOST": "  db  ", "DB_NAME": "   ", "DB_USER": ""},
            ["DB_HOST", "DB_NAME", "DB_USER"],
        )
    message = str(excinfo.value)
    assert "DB_NAME" in message
    assert "DB_USER" in message
    assert "DB_HOST" not in message
    assert require({"DB_HOST": "  db  "}, ["DB_HOST"]) == {"DB_HOST": "db"}


def test_require_keeps_secrets_unchanged():
    environ = {"DJANGO_SECRET_KEY": " key ", "DB_PASSWORD": "\tpass "}
    assert require(environ, ["DJANGO_SECRET_KEY", "DB_PASSWORD"]) == environ


# RF-20: booleanos estrictos


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("TRUE", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("", False),
        ("  ", False),
        (None, False),
    ],
)
def test_parse_bool_accepts_boolean_values(raw, expected):
    assert parse_bool("DJANGO_DEBUG", raw) is expected


@pytest.mark.parametrize("raw", ["yes", "on", "SENTINEL-BOOL"])
def test_parse_bool_rejects_non_boolean_naming_variable_without_value(raw):
    with pytest.raises(ImproperlyConfigured) as excinfo:
        parse_bool("DJANGO_DEBUG", raw)
    message = str(excinfo.value)
    assert "DJANGO_DEBUG" in message
    assert raw not in message


# RF-12: puerto


@pytest.mark.parametrize(
    ("raw", "expected"), [("1", 1), ("5432", 5432), ("65535", 65535)]
)
def test_parse_port_accepts_valid_range(raw, expected):
    assert parse_port("DB_PORT", raw) == expected


@pytest.mark.parametrize(
    "raw", ["abc", "0", "70000", "-1", "54.32", "8_0", "+80", "٨٠", " 80 "]
)
def test_parse_port_rejects_invalid_without_leaking_value(raw):
    with pytest.raises(ImproperlyConfigured) as excinfo:
        parse_port("DB_PORT", raw)
    message = str(excinfo.value)
    assert "DB_PORT" in message
    assert f"'{raw}'" not in message
    assert f'"{raw}"' not in message
    # La traza completa tampoco: el ValueError de int() incluiría el valor
    rendered = "".join(traceback.format_exception(excinfo.value))
    assert "ValueError" not in rendered
    if raw not in ("0", "-1"):
        assert raw not in message
        assert raw not in rendered


# RF-15: hosts permitidos


def test_parse_allowed_hosts_accepts_domain_subdomain_wildcard_and_ip_ignoring_blanks():
    raw = " example.com , .example.com ,, 192.168.1.10 ,[::1], localhost , "
    assert parse_allowed_hosts("DJANGO_ALLOWED_HOSTS", raw) == [
        "example.com",
        ".example.com",
        "192.168.1.10",
        "[::1]",
        "localhost",
    ]


@pytest.mark.parametrize(
    "bad_host",
    [
        "*",
        "http://example.com",
        "example.com:8000",
        "example.com/admin",
        "exa mple.com",
        "-bad.example.com",
        "*.example.com",
    ],
)
def test_parse_allowed_hosts_rejects_invalid_without_leaking_value(bad_host):
    with pytest.raises(ImproperlyConfigured) as excinfo:
        parse_allowed_hosts("DJANGO_ALLOWED_HOSTS", f"example.com,{bad_host}")
    message = str(excinfo.value)
    assert "DJANGO_ALLOWED_HOSTS" in message
    assert bad_host not in message
    assert "example.com" not in message


# RF-11 a RF-15: configuración de producción


def test_load_production_config_returns_parsed_values():
    config = load_production_config(
        valid_production_environ(
            DJANGO_ALLOWED_HOSTS=" example.com , .example.com, 10.0.0.1 "
        )
    )
    assert config.secret_key == SECRET_SENTINEL
    assert config.allowed_hosts == ("example.com", ".example.com", "10.0.0.1")
    assert config.db_host == "SENTINEL-HOST"
    assert config.db_port == 5432
    assert config.db_name == "SENTINEL-NAME"
    assert config.db_user == "SENTINEL-USER"
    assert config.db_password == PASSWORD_SENTINEL


def test_load_production_config_keeps_secrets_unchanged():
    secret_key = f" {SECRET_SENTINEL} "
    password = f"\t{PASSWORD_SENTINEL} "
    config = load_production_config(
        valid_production_environ(DJANGO_SECRET_KEY=secret_key, DB_PASSWORD=password)
    )
    assert config.secret_key == secret_key
    assert config.db_password == password


def test_load_production_config_strips_non_secret_values():
    config = load_production_config(
        valid_production_environ(
            DB_HOST=" SENTINEL-HOST ",
            DB_PORT=" 5432 ",
            DB_NAME="\tSENTINEL-NAME ",
            DB_USER=" SENTINEL-USER\t",
        )
    )
    assert config.db_host == "SENTINEL-HOST"
    assert config.db_port == 5432
    assert config.db_name == "SENTINEL-NAME"
    assert config.db_user == "SENTINEL-USER"


def test_load_production_config_names_all_missing_variables_at_once():
    message = production_error({})
    for name in PRODUCTION_REQUIRED:
        assert name in message


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_load_production_config_treats_blank_as_missing(blank):
    environ = valid_production_environ(DB_NAME=blank, DB_USER=blank)
    message = production_error(environ)
    assert "DB_NAME" in message
    assert "DB_USER" in message
    assert "DB_HOST" not in message
    assert_no_value_leaks(message, environ)


def test_load_production_config_treats_hosts_without_entries_as_missing():
    environ = valid_production_environ(DJANGO_ALLOWED_HOSTS=" , ,, ")
    message = production_error(environ)
    assert "DJANGO_ALLOWED_HOSTS" in message


@pytest.mark.parametrize("port", ["abc", "0", "70000"])
def test_load_production_config_rejects_malformed_port(port):
    environ = valid_production_environ(DB_PORT=port)
    message = production_error(environ)
    assert "DB_PORT" in message
    assert_no_value_leaks(message, environ)


def test_load_production_config_rejects_secret_key_of_49_characters():
    environ = valid_production_environ(DJANGO_SECRET_KEY="S" * 49)
    message = production_error(environ)
    assert "DJANGO_SECRET_KEY" in message
    assert_no_value_leaks(message, environ)


def test_load_production_config_accepts_secret_key_of_50_characters():
    config = load_production_config(
        valid_production_environ(DJANGO_SECRET_KEY="S" * 50)
    )
    assert config.secret_key == "S" * 50


def test_load_production_config_rejects_insecure_secret_key_even_if_long():
    environ = valid_production_environ(DJANGO_SECRET_KEY="insecure-" + "S" * 60)
    message = production_error(environ)
    assert "DJANGO_SECRET_KEY" in message
    assert_no_value_leaks(message, environ)


@pytest.mark.parametrize(
    "password", ["insecure-dev-db-password", "SENTINEL-insecure-PASSWORD"]
)
def test_load_production_config_rejects_insecure_db_password(password):
    environ = valid_production_environ(DB_PASSWORD=password)
    message = production_error(environ)
    assert "DB_PASSWORD" in message
    assert_no_value_leaks(message, environ)


@pytest.mark.parametrize("hosts", ["*", "http://example.com", "example.com,*"])
def test_load_production_config_rejects_invalid_hosts(hosts):
    environ = valid_production_environ(DJANGO_ALLOWED_HOSTS=hosts)
    message = production_error(environ)
    assert "DJANGO_ALLOWED_HOSTS" in message
    assert "http://" not in message
    assert "*" not in message


def test_load_production_config_accumulates_every_problem_without_values():
    environ = {
        "DJANGO_SECRET_KEY": "insecure-SENTINEL-short",
        "DJANGO_ALLOWED_HOSTS": "http://SENTINEL-HOSTS.example",
        "DB_PORT": "SENTINEL-PORT",
        "DB_PASSWORD": "insecure-SENTINEL-PASSWORD",
    }
    message = production_error(environ)
    for name in PRODUCTION_REQUIRED:
        assert name in message
    assert "SENTINEL" not in message
