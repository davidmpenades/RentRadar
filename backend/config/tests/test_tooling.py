import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings

BACKEND = Path(settings.BASE_DIR)
CONFIG = str(BACKEND / "pyproject.toml")


def run_clean(args, cwd):
    # Entorno limpio: PATH y variables DB_* (el entorno test las lee), sin DJANGO_ENV
    database = {k: v for k, v in os.environ.items() if k.startswith("DB_")}
    environ = {"PATH": os.environ["PATH"], "RUFF_NO_CACHE": "true", **database}
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=cwd,
        env=environ,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_process_runs_as_the_container_user():
    assert os.geteuid() == 10001


def test_suite_runs_in_the_test_environment():
    assert settings.SETTINGS_MODULE == "config.settings.test"


def test_pytest_without_environment_fails_when_a_test_fails(tmp_path):
    (tmp_path / "test_broken.py").write_text("def test_broken():\n    assert False\n")

    result = run_clean(
        [
            "pytest",
            "-c",
            CONFIG,
            "-o",
            "django_find_project=false",
            str(tmp_path),
        ],
        cwd=BACKEND,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 failed" in result.stdout


def test_ruff_check_rejects_a_file_with_violations(tmp_path):
    (tmp_path / "bad.py").write_text("import os\n")

    result = run_clean(["ruff", "check", "--config", CONFIG, str(tmp_path)], BACKEND)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "F401" in result.stdout


def test_ruff_format_rejects_an_unformatted_file(tmp_path):
    (tmp_path / "ugly.py").write_text("x   =   1\n")

    result = run_clean(
        ["ruff", "format", "--check", "--config", CONFIG, str(tmp_path)], BACKEND
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "ugly.py" in result.stdout


def test_ruff_accepts_the_backend_code():
    check = run_clean(["ruff", "check", "--config", CONFIG, "."], cwd=BACKEND)
    fmt = run_clean(["ruff", "format", "--check", "--config", CONFIG, "."], BACKEND)

    assert check.returncode == 0, check.stdout
    assert fmt.returncode == 0, fmt.stdout
