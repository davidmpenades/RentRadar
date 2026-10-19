#!/usr/bin/env python
import sys

from django.core.exceptions import ImproperlyConfigured


def main() -> None:
    from config.env import configure_settings_module

    try:
        configure_settings_module()
        from django.conf import settings

        # Fuerza la carga aquí: algunos subcomandos capturarían el error y seguirían
        settings.INSTALLED_APPS  # noqa: B018
    except ImproperlyConfigured as error:
        sys.exit(f"Error de configuración: {error}")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
