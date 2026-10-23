import importlib
import unicodedata
from types import SimpleNamespace

import pytest
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations import RunPython
from django.test.utils import CaptureQueriesContext
from django.utils.connection import ConnectionDoesNotExist

from apps.categories.models import Category
from apps.categories.services import save_category

seed_migration = importlib.import_module(
    "apps.categories.migrations.0002_seed_categories"
)

# Lista de la spec escrita a mano: no se importa de la migración
EXPECTED_SEED = {
    "ebike": "Bicicleta eléctrica",
    "caravan": "Caravana",
    "motorhome": "Autocaravana",
    "van": "Furgoneta",
    "pool": "Piscina",
    "barbecue": "Barbacoa",
    "sports-area": "Zona deportiva",
    "boat": "Barco",
    "kayak": "Kayak",
    "canoe": "Piragua",
    "other": "Otros",
}
MIGRATION_NODE = ("categories", "0002_seed_categories")


def seeded():
    rows = Category.objects.filter(slug__in=EXPECTED_SEED).values_list("slug", "name")
    return dict(rows)


def historical_apps():
    return MigrationLoader(connection).project_state(MIGRATION_NODE).apps


def schema_editor_for(target_connection):
    # La migración solo usa el alias de la conexión del schema_editor
    return SimpleNamespace(connection=target_connection)


@pytest.mark.django_db
def test_migrations_leave_the_eleven_seed_categories():
    assert seeded() == EXPECTED_SEED


@pytest.mark.django_db
@pytest.mark.parametrize("slug", list(EXPECTED_SEED))
def test_each_seed_category_passes_the_validation_service(slug):
    save_category(Category.objects.get(slug=slug))

    assert Category.objects.get(slug=slug).name == EXPECTED_SEED[slug]


def test_seed_constant_matches_the_spec_letter_by_letter():
    assert len(seed_migration.SEED) == len(EXPECTED_SEED)
    assert dict(seed_migration.SEED) == EXPECTED_SEED
    for _, name in seed_migration.SEED:
        assert unicodedata.is_normalized("NFC", name)


@pytest.mark.django_db
def test_reapplying_the_seed_restores_names_without_duplicates():
    Category.objects.filter(slug="pool").update(name="Piscina vieja")
    Category.objects.filter(slug="kayak").delete()

    seed_migration.apply_seed(historical_apps(), schema_editor_for(connection))

    assert seeded() == EXPECTED_SEED
    assert Category.objects.filter(slug__in=EXPECTED_SEED).count() == len(EXPECTED_SEED)


@pytest.mark.django_db
def test_applying_the_seed_twice_keeps_one_row_per_slug():
    apps = historical_apps()

    seed_migration.apply_seed(apps, schema_editor_for(connection))
    seed_migration.apply_seed(apps, schema_editor_for(connection))

    assert seeded() == EXPECTED_SEED
    assert Category.objects.filter(slug__in=EXPECTED_SEED).count() == len(EXPECTED_SEED)


@pytest.mark.django_db
def test_reverting_the_seed_deletes_only_its_categories():
    Category(slug="garden", name="Jardín").save()

    seed_migration.reverse_seed(historical_apps(), schema_editor_for(connection))

    assert not Category.objects.filter(slug__in=EXPECTED_SEED).exists()
    assert Category.objects.filter(slug="garden").exists()


def test_seed_is_one_reversible_atomic_operation():
    (operation,) = seed_migration.Migration.operations

    assert isinstance(operation, RunPython)
    assert operation.code is seed_migration.apply_seed
    assert operation.reverse_code is seed_migration.reverse_seed
    assert operation.reverse_code is not RunPython.noop
    assert seed_migration.Migration.atomic is True


@pytest.mark.django_db
def test_reverting_the_seed_issues_a_single_delete():
    apps = historical_apps()

    with CaptureQueriesContext(connection) as queries:
        seed_migration.reverse_seed(apps, schema_editor_for(connection))

    statements = [query["sql"].lstrip().upper() for query in queries.captured_queries]
    assert sum(sql.startswith("DELETE") for sql in statements) == 1


@pytest.mark.django_db
@pytest.mark.parametrize("function", ["apply_seed", "reverse_seed"])
def test_seed_writes_to_the_connection_being_migrated(function):
    apps = historical_apps()
    editor = schema_editor_for(SimpleNamespace(alias="missing"))

    with pytest.raises(ConnectionDoesNotExist):
        getattr(seed_migration, function)(apps, editor)
