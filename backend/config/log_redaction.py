import logging
from collections.abc import Iterable

REDACTED = "[REDACTED]"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOGGER_NAMES = ("django", "django.request", "django.security")


class RedactingFormatter(logging.Formatter):
    def __init__(self, secrets: Iterable[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El más largo primero: si un secreto contiene a otro, no queda ningún trozo
        self._secrets = sorted({s for s in secrets if s}, key=len, reverse=True)

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        # Un secreto muy corto puede destrozar el log, pero se redacta: es más seguro
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return text


def build_production_logging(secrets: Iterable[str]) -> dict:
    # Sustituye los handlers de Django (con mail_admins) y del raíz por uno que redacta
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "redacting": {
                "()": RedactingFormatter,
                "secrets": list(secrets),
                "fmt": LOG_FORMAT,
            },
        },
        "handlers": {
            "redacted_console": {
                "class": "logging.StreamHandler",
                "formatter": "redacting",
            },
        },
        "loggers": {
            name: {
                "handlers": ["redacted_console"],
                "level": "INFO",
                "propagate": False,
            }
            for name in LOGGER_NAMES
        },
        "root": {"handlers": ["redacted_console"], "level": "INFO"},
    }
