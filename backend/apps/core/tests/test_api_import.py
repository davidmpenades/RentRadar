import os
import subprocess
import sys

import pytest
from django.conf import settings

# Un módulo por proceso: en la sesión de pytest ya estarían cargados
MODULES = ["apps.core.api", "apps.core.negotiation", "rest_framework.views"]


def import_in_a_new_process(module):
    environ = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.test"}
    return subprocess.run(
        [sys.executable, "-c", f"import django; django.setup(); import {module}"],
        cwd=settings.BASE_DIR,
        env=environ,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("module", MODULES)
def test_a_module_can_be_the_first_one_imported_in_a_new_process(module):
    result = import_in_a_new_process(module)

    assert result.returncode == 0, result.stderr
