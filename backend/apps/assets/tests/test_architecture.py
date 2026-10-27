from django.db.migrations.loader import MigrationLoader


def test_the_asset_migration_does_not_depend_on_the_category_seed():
    plan = MigrationLoader(None).graph.forwards_plan(("assets", "0001_initial"))

    assert ("categories", "0001_initial") in plan
    assert ("categories", "0002_seed_categories") not in plan
