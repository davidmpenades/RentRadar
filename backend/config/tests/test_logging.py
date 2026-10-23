import logging

import pytest

from config.tests.conftest import DEVELOPMENT_ENVIRON, PRODUCTION_ENVIRON

DB_LOGGER = "django.db.backends"
ENVIRONMENTS = ["development", "test", "production"]


def load(load_settings, env):
    environ = PRODUCTION_ENVIRON if env == "production" else DEVELOPMENT_ENVIRON
    return load_settings(env, **environ)


@pytest.mark.parametrize("env", ENVIRONMENTS)
def test_sql_logger_is_fixed_to_info(load_settings, env):
    settings = load(load_settings, env)

    assert settings.LOGGING["loggers"][DB_LOGGER]["level"] == "INFO"


@pytest.mark.parametrize("env", ["development", "test"])
def test_base_logging_keeps_the_default_django_loggers(load_settings, env):
    settings = load(load_settings, env)

    assert settings.LOGGING["version"] == 1
    assert settings.LOGGING["disable_existing_loggers"] is False
    assert list(settings.LOGGING["loggers"]) == [DB_LOGGER]


def test_production_sql_logger_goes_through_the_redacting_handler(load_settings):
    settings = load(load_settings, "production")

    logger = settings.LOGGING["loggers"][DB_LOGGER]
    assert logger["handlers"] == ["redacted_console"]
    assert logger["propagate"] is False


def test_sql_logger_runs_at_info_or_above():
    assert logging.getLogger(DB_LOGGER).getEffectiveLevel() >= logging.INFO
