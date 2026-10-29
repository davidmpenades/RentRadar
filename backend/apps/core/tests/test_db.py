import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction

from apps.core.db import (
    CONSTRAINT_VIOLATED,
    codes_for_constraint,
    constraint_name,
    run_guarded,
)
from apps.core.errors import DomainValidationError

CODES = {
    "guarded_items_label_key": ("label", "label_taken"),
    "guarded_children_parent_fk": ("parent", "parent_not_found"),
}
ORPHAN_CHILD = "INSERT INTO guarded_children (parent_id) VALUES (-1)"


@pytest.fixture
def guarded_tables(db):
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TEMP TABLE guarded_items ("
            "id serial PRIMARY KEY, label text NOT NULL,"
            " CONSTRAINT guarded_items_label_key UNIQUE (label))"
        )
        cursor.execute("CREATE TEMP TABLE guarded_parents (id integer PRIMARY KEY)")
        cursor.execute(
            "CREATE TEMP TABLE guarded_children ("
            "parent_id integer CONSTRAINT guarded_children_parent_fk"
            " REFERENCES guarded_parents (id) DEFERRABLE INITIALLY DEFERRED)"
        )


def insert_item(label):
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO guarded_items (label) VALUES (%s)", [label])


def count_items():
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM guarded_items")
        return cursor.fetchone()[0]


def insert_duplicate():
    insert_item("a")
    insert_item("a")


def orphan_raises_at_once():
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(ORPHAN_CHILD)
            transaction.set_rollback(True)
    except IntegrityError:
        return True
    return False


@pytest.mark.django_db
def test_known_constraint_is_translated_and_the_whole_block_is_rolled_back(
    guarded_tables,
):
    result, codes = run_guarded(insert_duplicate, CODES)

    assert (result, codes) == (None, {"label": ["label_taken"]})
    assert count_items() == 0


@pytest.mark.django_db
def test_unknown_constraint_is_reported_without_details(guarded_tables):
    assert run_guarded(insert_duplicate, {}) == (
        None,
        {"__all__": [CONSTRAINT_VIOLATED]},
    )


@pytest.mark.django_db
def test_violation_without_a_constraint_name_is_not_taken_for_success(guarded_tables):
    # Un NOT NULL no informa de ninguna restricción con nombre
    result, codes = run_guarded(lambda: insert_item(None), CODES)

    assert (result, codes) == (None, {"__all__": [CONSTRAINT_VIOLATED]})


@pytest.mark.django_db
def test_integrity_error_without_diagnostics_is_not_swallowed(guarded_tables):
    def fail():
        raise IntegrityError("sin diagnóstico")

    assert run_guarded(fail, CODES) == (None, {"__all__": [CONSTRAINT_VIOLATED]})


def test_unknown_constraint_name_maps_to_the_generic_code():
    assert codes_for_constraint("other_constraint", CODES) == {
        "__all__": [CONSTRAINT_VIOLATED]
    }


def test_missing_constraint_name_is_an_empty_string():
    assert constraint_name(IntegrityError("sin causa")) == ""


@pytest.mark.django_db
def test_connection_stays_usable_after_the_translated_error(guarded_tables):
    run_guarded(insert_duplicate, CODES)

    insert_item("b")

    assert count_items() == 1


@pytest.mark.django_db
def test_database_error_is_propagated(guarded_tables):
    def fail():
        raise DatabaseError("boom")

    with pytest.raises(DatabaseError, match="boom"):
        run_guarded(fail, CODES)


@pytest.mark.django_db
def test_domain_error_raised_inside_rolls_back_and_keeps_no_context(guarded_tables):
    def write():
        insert_item("a")
        raise DomainValidationError({"label": ["label_invalid"]})

    with pytest.raises(DomainValidationError) as raised:
        run_guarded(write, CODES)

    assert raised.value.message_dict == {"label": ["label_invalid"]}
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert count_items() == 0


@pytest.mark.django_db
def test_result_of_the_block_is_returned(guarded_tables):
    def write():
        insert_item("a")
        return "saved"

    assert run_guarded(write, CODES) == ("saved", {})
    assert count_items() == 1


@pytest.mark.django_db
def test_violated_foreign_key_surfaces_inside_the_block_and_is_translated(
    guarded_tables,
):
    def write():
        with connection.cursor() as cursor:
            cursor.execute(ORPHAN_CHILD)

    assert run_guarded(write, CODES) == (None, {"parent": ["parent_not_found"]})


@pytest.mark.django_db
@pytest.mark.parametrize("outcome", ["saved", "violated"])
def test_constraints_are_deferred_again_after_the_block(guarded_tables, outcome):
    run_guarded(lambda: insert_item("a"), CODES)
    if outcome == "violated":
        run_guarded(insert_duplicate, CODES)

    assert not orphan_raises_at_once()
