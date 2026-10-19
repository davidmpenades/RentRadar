import io
import logging
import logging.config
import sys

import pytest

from config.log_redaction import (
    LOGGER_NAMES,
    RedactingFormatter,
    build_production_logging,
)
from config.tests.conftest import (
    PASSWORD_SENTINEL,
    PRODUCTION_ENVIRON,
    SECRET_SENTINEL,
)

ROOT_LOGGER = ""


def make_record(message):
    return logging.LogRecord("test", logging.ERROR, __file__, 1, message, None, None)


def redact(secrets, message):
    return RedactingFormatter(secrets, fmt="%(message)s").format(make_record(message))


@pytest.fixture
def production_logging(settings):
    saved = {
        name: (
            logging.getLogger(name).handlers[:],
            logging.getLogger(name).propagate,
            logging.getLogger(name).level,
        )
        for name in (*LOGGER_NAMES, ROOT_LOGGER)
    }
    settings.ROOT_URLCONF = "config.tests.urls"
    settings.ALLOWED_HOSTS = ["example.com"]
    stream = io.StringIO()
    config = build_production_logging((SECRET_SENTINEL, PASSWORD_SENTINEL))
    for handler in config["handlers"].values():
        handler["stream"] = stream
    logging.config.dictConfig(config)
    yield stream
    for name, (handlers, propagate, level) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers[:] = handlers
        logger.propagate = propagate
        logger.setLevel(level)


def test_unhandled_error_is_logged_without_secrets(client, production_logging):
    client.raise_request_exception = False
    message = f"key={SECRET_SENTINEL} password={PASSWORD_SENTINEL}"

    client.get("/leak/", {"message": message}, headers={"host": "example.com"})

    log = production_logging.getvalue()
    assert "Internal Server Error" in log
    assert "RuntimeError" in log
    assert SECRET_SENTINEL not in log
    assert PASSWORD_SENTINEL not in log


def test_non_django_logger_is_redacted(production_logging):
    logger = logging.getLogger("apps.core")

    logger.error("failed key=%s password=%s", SECRET_SENTINEL, PASSWORD_SENTINEL)

    log = production_logging.getvalue()
    assert "[REDACTED]" in log
    assert SECRET_SENTINEL not in log
    assert PASSWORD_SENTINEL not in log


def test_longest_secret_is_replaced_first():
    result = redact(("PASS", "abc-PASS-xyz"), "key=abc-PASS-xyz")

    assert result == "key=[REDACTED]"


def test_very_short_secret_is_redacted_even_if_the_log_becomes_unreadable():
    result = redact(("a",), "a banana")

    assert "a" not in result
    assert "banana" not in result


def test_empty_secrets_are_ignored():
    assert redact(("", "x"), "plain message") == "plain message"


def test_secret_in_traceback_is_redacted():
    try:
        raise RuntimeError(f"boom {PASSWORD_SENTINEL}")
    except RuntimeError:
        record = logging.LogRecord(
            "test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )

    result = RedactingFormatter((PASSWORD_SENTINEL,), fmt="%(message)s").format(record)

    assert "Traceback" in result
    assert PASSWORD_SENTINEL not in result


def test_only_the_redacting_handler_is_configured():
    config = build_production_logging(("secret",))

    assert list(config["handlers"]) == ["redacted_console"]
    for name in LOGGER_NAMES:
        assert config["loggers"][name]["handlers"] == ["redacted_console"]
    assert config["root"]["handlers"] == ["redacted_console"]


def test_production_settings_wire_the_redaction_without_admins(load_settings):
    module = load_settings("production", **PRODUCTION_ENVIRON)

    formatter = module.LOGGING["formatters"]["redacting"]
    assert set(formatter["secrets"]) == {SECRET_SENTINEL, PASSWORD_SENTINEL}
    assert not getattr(module, "ADMINS", [])
