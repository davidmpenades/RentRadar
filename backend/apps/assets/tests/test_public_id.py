import importlib
import uuid
from types import SimpleNamespace

import pytest
from django.db import IntegrityError, connection, models, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations import AddField, AlterField, RunPython
from django.forms import modelform_factory
from django.test.utils import CaptureQueriesContext
from django.utils.connection import ConnectionDoesNotExist

from apps.assets.models import Asset
from apps.assets.services import create_asset, update_asset
from apps.assets.tests.conftest import NOW
from apps.assets.tests.test_update import MOVED

add_migration = importlib.import_module("apps.assets.migrations.0002_asset_public_id")
fill_migration = importlib.import_module(
    "apps.assets.migrations.0003_fill_asset_public_id"
)
alter_migration = importlib.import_module(
    "apps.assets.migrations.0004_alter_asset_public_id"
)

# Nombre que la BD da a la restricción única, tomado del SQL de sqlmigrate
UNIQUE_CONSTRAINT = "assets_asset_public_id_f569762c_uniq"
STATE_BEFORE_FILL = ("assets", "0002_asset_public_id")
ROWS = 3


def historical_apps():
    return MigrationLoader(connection).project_state(STATE_BEFORE_FILL).apps


def schema_editor_for(target_connection):
    # Las migraciones solo usan el alias de la conexión del schema_editor
    return SimpleNamespace(connection=target_connection)


def statements_of(captured):
    return [query["sql"].lstrip().upper() for query in captured.captured_queries]


def updates_of(captured):
    return [
        query["sql"]
        for query in captured.captured_queries
        if query["sql"].lstrip().upper().startswith("UPDATE")
    ]


@pytest.fixture
def rows_without_public_id(make_asset):
    # Los bienes que habría antes del relleno: la columna admite nulos y todos lo son
    for number in range(ROWS):
        make_asset(title=f"Taladro {number}").save()
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("ALTER TABLE assets_asset ALTER COLUMN public_id DROP NOT NULL")
    Asset.objects.update(public_id=None)


def test_the_field_is_a_required_unique_uuid_generated_by_uuid4():
    field = Asset._meta.get_field("public_id")

    assert isinstance(field, models.UUIDField)
    assert field.default is uuid.uuid4
    assert field.unique is True
    assert field.null is False


def test_the_field_is_not_editable_and_stays_out_of_forms():
    field = Asset._meta.get_field("public_id")

    assert field.editable is False
    assert "public_id" not in modelform_factory(Asset, fields="__all__").base_fields


def test_a_created_asset_gets_a_version_4_uuid_that_is_not_its_primary_key(
    stored_asset,
):
    stored = Asset.objects.get(pk=stored_asset.pk)

    assert isinstance(stored.public_id, uuid.UUID)
    assert stored.public_id.version == 4
    assert stored.public_id.int != stored.pk
    assert str(stored.public_id) != str(stored.pk)


def test_each_asset_gets_its_own_uuid(creation_arguments):
    first = create_asset(**creation_arguments)
    second = create_asset(**creation_arguments)

    assert first.public_id != second.public_id


def test_an_asset_built_directly_also_gets_a_version_4_uuid(make_asset):
    first, second = make_asset(), make_asset()

    assert first.public_id.version == 4
    assert first.public_id != second.public_id


def test_the_database_rejects_a_repeated_public_id_by_name(make_asset):
    first = make_asset()
    first.save()

    with pytest.raises(IntegrityError) as caught, transaction.atomic():
        make_asset(public_id=first.public_id).save()

    assert caught.value.__cause__.diag.constraint_name == UNIQUE_CONSTRAINT


def test_the_unique_constraint_is_the_only_unique_one_on_the_column(db):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT c.conname FROM pg_constraint c"
            " JOIN pg_attribute a ON a.attrelid = c.conrelid"
            " AND a.attnum = ANY (c.conkey)"
            " WHERE c.conrelid = 'assets_asset'::regclass"
            " AND c.contype = 'u' AND a.attname = 'public_id'"
        )
        names = [row[0] for row in cursor.fetchall()]

    assert names == [UNIQUE_CONSTRAINT]


def reactivate_then_pause(asset):
    update_asset(now=NOW, asset_id=asset.pk, status="active")
    update_asset(now=NOW, asset_id=asset.pk, status="paused")


OPERATIONS = {
    "edit": lambda asset: update_asset(now=NOW, asset_id=asset.pk, title="Martillo"),
    "activate": lambda asset: update_asset(now=NOW, asset_id=asset.pk, status="active"),
    "pause_and_reactivate": reactivate_then_pause,
    "move_while_paused": lambda asset: update_asset(
        now=NOW, asset_id=asset.pk, **MOVED
    ),
}


@pytest.mark.parametrize("operation", OPERATIONS.values(), ids=OPERATIONS)
def test_no_service_changes_the_public_id(stored_asset, operation):
    before = Asset.objects.get(pk=stored_asset.pk).public_id

    with CaptureQueriesContext(connection) as captured:
        operation(stored_asset)

    assert Asset.objects.get(pk=stored_asset.pk).public_id == before
    assert updates_of(captured)
    assert all("public_id" not in update for update in updates_of(captured))


def test_the_services_do_not_accept_a_public_id(creation_arguments, stored_asset):
    with pytest.raises(TypeError):
        create_asset(**creation_arguments, public_id=uuid.uuid4())
    with pytest.raises(TypeError):
        update_asset(now=NOW, asset_id=stored_asset.pk, public_id=uuid.uuid4())


def test_the_first_migration_adds_a_nullable_column_without_default_or_unique():
    (operation,) = add_migration.Migration.operations

    assert isinstance(operation, AddField)
    assert operation.field.null is True
    assert operation.field.has_default() is False
    assert operation.field.unique is False
    assert add_migration.Migration.dependencies == [("assets", "0001_initial")]


def test_the_last_migration_makes_the_column_required_unique_and_uuid4():
    (operation,) = alter_migration.Migration.operations

    assert isinstance(operation, AlterField)
    assert operation.field.null is False
    assert operation.field.unique is True
    assert operation.field.editable is False
    assert operation.field.default is uuid.uuid4
    assert alter_migration.Migration.dependencies == [
        ("assets", "0003_fill_asset_public_id")
    ]


def test_the_fill_is_one_reversible_atomic_operation_after_the_column_exists():
    (operation,) = fill_migration.Migration.operations

    assert isinstance(operation, RunPython)
    assert operation.code is fill_migration.fill_public_id
    assert operation.reverse_code is fill_migration.unfill_public_id
    assert operation.reverse_code is not RunPython.noop
    assert fill_migration.Migration.atomic is True
    assert fill_migration.Migration.dependencies == [("assets", "0002_asset_public_id")]


@pytest.mark.django_db
def test_filling_gives_each_row_its_own_version_4_uuid(rows_without_public_id):
    fill_migration.fill_public_id(historical_apps(), schema_editor_for(connection))

    values = list(Asset.objects.values_list("public_id", flat=True))
    assert len(values) == ROWS
    assert None not in values
    assert len(set(values)) == ROWS
    assert {value.version for value in values} == {4}


@pytest.mark.django_db
def test_filling_keeps_the_value_of_a_row_that_already_has_one(rows_without_public_id):
    kept = Asset.objects.order_by("pk").first()
    Asset.objects.filter(pk=kept.pk).update(public_id=uuid.UUID(int=7, version=4))

    fill_migration.fill_public_id(historical_apps(), schema_editor_for(connection))

    assert Asset.objects.get(pk=kept.pk).public_id == uuid.UUID(int=7, version=4)
    assert Asset.objects.filter(public_id__isnull=True).count() == 0


@pytest.mark.django_db
def test_unfilling_nulls_every_value_with_one_update_and_deletes_nothing(
    rows_without_public_id,
):
    fill_migration.fill_public_id(historical_apps(), schema_editor_for(connection))

    with CaptureQueriesContext(connection) as captured:
        fill_migration.unfill_public_id(
            historical_apps(), schema_editor_for(connection)
        )

    statements = statements_of(captured)
    assert sum(sql.startswith("UPDATE") for sql in statements) == 1
    assert not any(sql.startswith("DELETE") for sql in statements)
    assert Asset.objects.count() == ROWS
    assert Asset.objects.filter(public_id__isnull=True).count() == ROWS


@pytest.mark.django_db
@pytest.mark.parametrize("function", ["fill_public_id", "unfill_public_id"])
def test_the_backfill_writes_to_the_connection_being_migrated(function):
    editor = schema_editor_for(SimpleNamespace(alias="missing"))

    with pytest.raises(ConnectionDoesNotExist):
        getattr(fill_migration, function)(historical_apps(), editor)
