import os
import subprocess
import sys

import pytest
from django.conf import settings

ENTRYPOINTS = {
    "manage.py": [sys.executable, "manage.py", "check"],
    "wsgi": [sys.executable, "-c", "import config.wsgi"],
    "asgi": [sys.executable, "-c", "import config.asgi"],
}


def run(command, django_env):
    environ = {
        name: value
        for name, value in os.environ.items()
        if name not in {"DJANGO_ENV", "DJANGO_SETTINGS_MODULE"}
    }
    if django_env is not None:
        environ["DJANGO_ENV"] = django_env
    return subprocess.run(
        command,
        cwd=settings.BASE_DIR,
        env=environ,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("entrypoint", ENTRYPOINTS)
@pytest.mark.parametrize("django_env", [None, "Production", "prod"])
def test_entrypoint_refuses_unknown_environment(entrypoint, django_env):
    result = run(ENTRYPOINTS[entrypoint], django_env)

    assert result.returncode != 0
    assert "development, test, production" in result.stderr


def test_manage_py_reports_without_traceback():
    result = run(ENTRYPOINTS["manage.py"], "prod")

    assert result.stderr.startswith("Error de configuración:")
    assert "Traceback" not in result.stderr


def test_manage_py_check_passes_in_development():
    result = run(ENTRYPOINTS["manage.py"], "development")

    assert result.returncode == 0, result.stderr
