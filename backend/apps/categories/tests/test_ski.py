import importlib
import unicodedata
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations import RunPython
from django.db.migrations.recorder import MigrationRecorder
from django.test.utils import CaptureQueriesContext
from django.utils.connection import ConnectionDoesNotExist

from apps.categories.models import Category
from apps.categories.services import save_category

MODULE = "apps.categories.migrations.0003_add_ski_category"
SKI_NODE = ("categories", "0003_add_ski_category")
SEED_NODE = ("categories", "0002_seed_categories")
SKI_NAME = "Esquí"
# Lista de la spec escrita a mano: no se importa de la migración de la semilla
SEED = {
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
# Nombres que coinciden con «Esquí» sin distinguir mayúsculas ni forma Unicode
CONFLICTING_NAMES = {
    "lowercase": "esquí",
    "uppercase": "ESQUÍ",
    "decomposed": unicodedata.normalize("NFD", SKI_NAME),
}


def ski_migration():
    # Se importa dentro de cada test: sin la migración falla cada uno por su cuenta
    return importlib.import_module(MODULE)


def historical_apps():
    return MigrationLoader(connection).project_state(SKI_NODE).apps


def schema_editor_for(target_connection):
    # La migración solo usa el alias de la conexión del schema_editor
    return SimpleNamespace(connection=target_connection)


def catalogue():
    return set(Category.objects.values_list("slug", "name"))


def ski_migration_applied():
    return SKI_NODE in MigrationRecorder(connection).applied_migrations()


@pytest.mark.django_db
def test_migrations_leave_ski_next_to_the_eleven_seed_categories():
    assert catalogue() == set(SEED.items()) | {("ski", SKI_NAME)}


@pytest.mark.django_db
def test_the_ski_name_is_nfc_with_five_characters_and_passes_validation():
    save_category(Category.objects.get(slug="ski"))

    name = Category.objects.get(slug="ski").name
    assert name == SKI_NAME
    assert unicodedata.is_normalized("NFC", name)
    assert len(name) == 5


@pytest.mark.django_db
@pytest.mark.parametrize("current_name", [None, "Nieve", "esquí"])
def test_reapplying_leaves_one_ski_with_its_name(current_name):
    migration = ski_migration()
    if current_name is None:
        Category.objects.filter(slug="ski").delete()
    else:
        Category.objects.filter(slug="ski").update(name=current_name)

    migration.apply_ski(historical_apps(), schema_editor_for(connection))

    assert catalogue() == set(SEED.items()) | {("ski", SKI_NAME)}
    assert Category.objects.filter(slug="ski").count() == 1


@pytest.mark.django_db
def test_applying_twice_keeps_one_ski():
    migration = ski_migration()
    apps = historical_apps()

    migration.apply_ski(apps, schema_editor_for(connection))
    migration.apply_ski(apps, schema_editor_for(connection))

    assert Category.objects.filter(slug="ski").count() == 1
    assert catalogue() == set(SEED.items()) | {("ski", SKI_NAME)}


@pytest.mark.django_db
@pytest.mark.parametrize("name", CONFLICTING_NAMES.values(), ids=CONFLICTING_NAMES)
def test_a_category_with_the_same_name_fails_before_writing_anything(name):
    migration = ski_migration()
    Category.objects.filter(slug="ski").delete()
    Category.objects.create(slug="winter-sports", name=name)
    before = catalogue()

    with pytest.raises(migration.SkiNameTakenError) as raised:
        migration.apply_ski(historical_apps(), schema_editor_for(connection))

    assert catalogue() == before
    assert not Category.objects.filter(slug="ski").exists()
    assert "winter-sports" not in str(raised.value)


@pytest.mark.django_db
def test_a_conflict_leaves_an_existing_ski_with_its_name():
    migration = ski_migration()
    Category.objects.filter(slug="ski").update(name="Nieve")
    Category.objects.create(slug="winter-sports", name="esquí")

    with pytest.raises(migration.SkiNameTakenError):
        migration.apply_ski(historical_apps(), schema_editor_for(connection))

    assert Category.objects.get(slug="ski").name == "Nieve"


@pytest.mark.django_db
def test_migrating_with_a_conflicting_name_fails_and_stays_unapplied():
    migration = ski_migration()
    with transaction.atomic():
        call_command("migrate", "categories", SEED_NODE[1], verbosity=0)
        Category.objects.create(slug="winter-sports", name="esquí")
        before = catalogue()

        with pytest.raises(migration.SkiNameTakenError):
            call_command("migrate", "categories", verbosity=0)

        assert catalogue() == before
        assert not ski_migration_applied()
        # Deja la BD como estaba para los demás tests
        transaction.set_rollback(True)


@pytest.mark.django_db
def test_reverting_deletes_only_ski():
    migration = ski_migration()
    Category.objects.create(slug="garden", name="Jardín")

    migration.reverse_ski(historical_apps(), schema_editor_for(connection))

    assert catalogue() == set(SEED.items()) | {("garden", "Jardín")}


@pytest.mark.django_db
def test_reverting_and_migrating_again_recreates_ski():
    assert Category.objects.filter(slug="ski").exists()
    with transaction.atomic():
        call_command("migrate", "categories", SEED_NODE[1], verbosity=0)
        assert not Category.objects.filter(slug="ski").exists()
        assert not ski_migration_applied()

        call_command("migrate", "categories", verbosity=0)
        assert Category.objects.get(slug="ski").name == SKI_NAME
        assert ski_migration_applied()
        transaction.set_rollback(True)


@pytest.mark.django_db
def test_reverting_issues_a_single_delete():
    migration = ski_migration()
    apps = historical_apps()

    with CaptureQueriesContext(connection) as queries:
        migration.reverse_ski(apps, schema_editor_for(connection))

    statements = [query["sql"].lstrip().upper() for query in queries.captured_queries]
    assert sum(sql.startswith("DELETE") for sql in statements) == 1


@pytest.mark.django_db
@pytest.mark.parametrize("function", ["apply_ski", "reverse_ski"])
def test_ski_writes_to_the_connection_being_migrated(function):
    migration = ski_migration()
    apps = historical_apps()
    editor = schema_editor_for(SimpleNamespace(alias="missing"))

    with pytest.raises(ConnectionDoesNotExist):
        getattr(migration, function)(apps, editor)


def test_the_migration_depends_only_on_the_seed():
    assert ski_migration().Migration.dependencies == [SEED_NODE]


def test_ski_is_one_reversible_atomic_operation():
    migration = ski_migration()
    (operation,) = migration.Migration.operations

    assert isinstance(operation, RunPython)
    assert operation.code is migration.apply_ski
    assert operation.reverse_code is migration.reverse_ski
    assert operation.reverse_code is not RunPython.noop
    assert migration.Migration.atomic is True
