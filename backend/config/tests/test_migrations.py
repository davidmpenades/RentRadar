import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_models_have_no_pending_migrations():
    # En proceso: un subproceso con manage.py usaría la BD de desarrollo
    try:
        call_command(
            "makemigrations", check_changes=True, dry_run=True, interactive=False
        )
    except SystemExit:
        pytest.fail("Hay cambios de modelos sin migración: ejecuta makemigrations.")
