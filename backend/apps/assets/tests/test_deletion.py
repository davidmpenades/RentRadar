import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import ProtectedError

from apps.assets.models import Asset
from apps.categories.models import Category
from apps.users.models import User

SEED_SIZE = 11
CATALOGUE_SIZE = 12
SKI_MIGRATION = ("categories", "0003_add_ski_category")
REFERENCES = {
    "owner": (
        User,
        "owner_id",
        "assets_asset_owner_id_23c9aaf7_fk_users_user_id",
    ),
    "category": (
        Category,
        "category_id",
        "assets_asset_category_id_b30c6baf_fk_categories_category_id",
    ),
}


def seed_state():
    applied = MigrationRecorder(connection).applied_migrations()
    return Category.objects.count(), ("categories", "0002_seed_categories") in applied


def ski_migration_applied():
    return SKI_MIGRATION in MigrationRecorder(connection).applied_migrations()


@pytest.mark.parametrize(
    ("model", "attribute", "constraint"), REFERENCES.values(), ids=REFERENCES
)
def test_deleting_a_referenced_row_by_sql_violates_the_foreign_key(
    stored_asset, model, attribute, constraint
):
    referenced_id = getattr(stored_asset, attribute)
    table = connection.ops.quote_name(model._meta.db_table)

    with (
        pytest.raises(IntegrityError) as caught,
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute(f"DELETE FROM {table} WHERE id = %s", [referenced_id])

    assert caught.value.__cause__.diag.constraint_name == constraint
    assert model.objects.filter(pk=referenced_id).exists()
    assert Asset.objects.filter(pk=stored_asset.pk).exists()


def test_reverting_the_seed_with_an_asset_is_rejected_and_keeps_the_seed(stored_asset):
    assert seed_state() == (CATALOGUE_SIZE, True)
    assert ski_migration_applied()

    with transaction.atomic():
        with pytest.raises(ProtectedError):
            call_command("migrate", "categories", "0001_initial", verbosity=0)
        # La reversión de Esquí ya se confirmó antes de que falle la de la semilla
        assert not Category.objects.filter(slug="ski").exists()
        assert seed_state() == (SEED_SIZE, True)
        assert not ski_migration_applied()
        assert Asset.objects.filter(pk=stored_asset.pk).exists()
        # Esto deshace también la reversión de Esquí para los demás tests
        transaction.set_rollback(True)

    assert seed_state() == (CATALOGUE_SIZE, True)
    assert ski_migration_applied()
    assert Asset.objects.filter(pk=stored_asset.pk).exists()
