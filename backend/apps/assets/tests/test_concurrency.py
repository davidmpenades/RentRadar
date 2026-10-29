import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.assets.services import update_asset
from apps.assets.tests.conftest import NOW

CHANGES = {
    "title": {"title": "Martillo"},
    "exact_location": {"latitude": 40.5, "longitude": -3.6},
}


def statements_of(change):
    with CaptureQueriesContext(connection) as captured:
        update_asset(now=NOW, **change)
    return [query["sql"].strip() for query in captured.captured_queries]


def index_of(statements, matches):
    return next(position for position, sql in enumerate(statements) if matches(sql))


def names_the_asset_table(sql):
    return '"assets_asset"' in sql


@pytest.mark.parametrize("change", CHANGES.values(), ids=CHANGES)
def test_the_row_is_locked_before_anything_else_reads_the_asset(stored_asset, change):
    statements = statements_of({"asset_id": stored_asset.pk, **change})

    first_on_the_asset = index_of(statements, names_the_asset_table)
    assert statements[first_on_the_asset].startswith("SELECT")
    assert statements[first_on_the_asset].endswith("FOR UPDATE")


@pytest.mark.parametrize("change", CHANGES.values(), ids=CHANGES)
def test_the_update_comes_after_the_lock_in_the_same_transaction(stored_asset, change):
    statements = statements_of({"asset_id": stored_asset.pk, **change})

    savepoint = index_of(statements, lambda sql: sql.startswith("SAVEPOINT"))
    lock = index_of(statements, lambda sql: sql.endswith("FOR UPDATE"))
    update = index_of(statements, lambda sql: sql.startswith('UPDATE "assets_asset"'))
    release = index_of(statements, lambda sql: sql.startswith("RELEASE SAVEPOINT"))
    assert savepoint < lock < update < release
