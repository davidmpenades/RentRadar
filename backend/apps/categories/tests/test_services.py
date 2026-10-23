import unicodedata

import pytest
from django.db import DatabaseError, IntegrityError

from apps.categories import services
from apps.categories.models import Category
from apps.categories.services import save_category
from apps.core.errors import DomainValidationError

# Letra con tilde compuesta (NFC): cuenta como un carácter
ACCENTED = "é"
GARDEN = "Jardín"
PLAN_ERROR_CODES = {
    "slug_empty",
    "slug_invalid",
    "slug_too_long",
    "slug_taken",
    "slug_immutable",
    "name_empty",
    "name_invalid",
    "name_control_char",
    "name_too_long",
    "name_taken",
    "constraint_violated",
    "validation_failed",
}


def codes_of(raised):
    return {field: set(codes) for field, codes in raised.value.message_dict.items()}


def skip_validation(monkeypatch):
    # Simula la carrera: otra alta entra entre la validación y el INSERT
    monkeypatch.setattr(Category, "full_clean", lambda self, *args, **kwargs: None)


def stored(slug):
    return Category.objects.get(slug=slug)


@pytest.fixture
def category_count():
    # La semilla ya trae categorías: se compara contra el recuento previo
    before = Category.objects.count()
    return lambda: Category.objects.count() - before


@pytest.mark.django_db
def test_valid_category_is_saved():
    category = save_category(Category(slug="garden", name=GARDEN))

    assert category.pk is not None
    assert stored("garden").name == GARDEN


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("Ebike", {"slug_invalid"}),
        ("e bike", {"slug_invalid"}),
        ("-ebike", {"slug_invalid"}),
        ("ebike-", {"slug_invalid"}),
        ("e--bike", {"slug_invalid"}),
        ("e_bike", {"slug_invalid"}),
        ("", {"slug_empty"}),
        (123, {"slug_invalid"}),
    ],
)
def test_invalid_slugs_are_rejected(category_count, slug, expected):
    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug=slug, name=GARDEN))

    assert codes_of(raised) == {"slug": expected}
    assert category_count() == 0


@pytest.mark.django_db
def test_slug_with_hyphens_and_digits_is_accepted():
    save_category(Category(slug="e-bike-2", name=GARDEN))

    assert stored("e-bike-2").name == GARDEN


@pytest.mark.django_db
def test_slug_of_50_characters_is_accepted():
    save_category(Category(slug="a" * 50, name=GARDEN))

    assert stored("a" * 50).name == GARDEN


@pytest.mark.django_db
def test_slug_of_51_characters_is_too_long(category_count):
    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="a" * 51, name=GARDEN))

    assert codes_of(raised) == {"slug": {"slug_too_long"}}
    assert category_count() == 0


@pytest.mark.django_db
def test_repeated_slug_is_taken(category_count):
    save_category(Category(slug="garden", name=GARDEN))

    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="garden", name="Tienda"))

    assert codes_of(raised) == {"slug": {"slug_taken"}}
    assert category_count() == 1


@pytest.mark.django_db
def test_concurrent_repeated_slug_is_translated_to_slug_taken(
    monkeypatch, category_count
):
    Category(slug="garden", name=GARDEN).save()
    skip_validation(monkeypatch)

    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="garden", name="Tienda"))

    assert codes_of(raised) == {"slug": {"slug_taken"}}
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    # La conexión sigue usable tras el rollback del atomic
    assert category_count() == 1


@pytest.mark.django_db
def test_blank_name_is_empty(category_count):
    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="garden", name="   "))

    assert codes_of(raised) == {"name": {"name_empty"}}
    assert category_count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["Tien\tda", "Tien\x00da"], ids=["tab", "null"])
def test_name_with_a_control_character_is_rejected(category_count, name):
    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="garden", name=name))

    assert codes_of(raised) == {"name": {"name_control_char"}}
    assert category_count() == 0


@pytest.mark.django_db
def test_non_text_name_is_invalid(category_count):
    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="garden", name=123))

    assert codes_of(raised) == {"name": {"name_invalid"}}
    assert category_count() == 0


@pytest.mark.django_db
def test_slug_and_name_errors_are_reported_together():
    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="Bad Slug", name="   "))

    assert codes_of(raised) == {
        "slug": {"slug_invalid"},
        "name": {"name_empty"},
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name",
    ["  tienda  ", "TIENDA", unicodedata.normalize("NFD", "Tienda")],
    ids=["trimmed", "uppercase", "decomposed"],
)
def test_name_matching_another_one_ignoring_case_is_taken(category_count, name):
    save_category(Category(slug="tent", name="Tienda"))

    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="camp", name=name))

    assert codes_of(raised) == {"name": {"name_taken"}}
    assert category_count() == 1


@pytest.mark.django_db
def test_decomposed_name_matches_the_composed_one():
    save_category(Category(slug="garden", name=GARDEN))

    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="yard", name=unicodedata.normalize("NFD", GARDEN)))

    assert codes_of(raised) == {"name": {"name_taken"}}


@pytest.mark.django_db
@pytest.mark.parametrize("renamed", [False, True], ids=["new", "renamed"])
def test_concurrent_repeated_name_is_translated_to_name_taken(
    monkeypatch, category_count, renamed
):
    Category(slug="tent", name="Tienda").save()
    category = Category(slug="camp", name="TIENDA")
    if renamed:
        # Ya guardada: el guardado es un UPDATE con update_fields=["name"]
        Category(slug="camp", name="Campamento").save()
        category = Category.objects.get(slug="camp")
        category.name = "TIENDA"
    skip_validation(monkeypatch)

    with pytest.raises(DomainValidationError) as raised:
        save_category(category)

    assert codes_of(raised) == {"name": {"name_taken"}}
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert category_count() == (2 if renamed else 1)
    if renamed:
        assert stored("camp").name == "Campamento"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name",
    [ACCENTED * 60, unicodedata.normalize("NFD", ACCENTED * 60)],
    ids=["composed", "decomposed"],
)
def test_name_of_60_characters_is_accepted(name):
    save_category(Category(slug="garden", name=name))

    assert stored("garden").name == ACCENTED * 60


@pytest.mark.django_db
def test_name_of_61_characters_is_too_long(category_count):
    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="garden", name=ACCENTED * 61))

    assert codes_of(raised) == {"name": {"name_too_long"}}
    assert category_count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name",
    [" Jardín ", "\u00a0Jardín\u00a0", "Jardi\u0301n"],
    ids=["spaces", "nbsp", "decomposed"],
)
def test_name_is_stored_trimmed_and_composed(name):
    category = save_category(Category(slug="garden", name=name))

    assert category.name == GARDEN
    assert stored("garden").name == GARDEN


@pytest.mark.django_db
def test_renamed_category_is_stored_trimmed_and_composed():
    category = save_category(Category(slug="garden", name=GARDEN))
    category.name = " Huerto\u00a0"

    save_category(category)

    assert stored("garden").name == "Huerto"


@pytest.mark.django_db
def test_instance_keeps_the_normalized_name_after_a_rejection():
    save_category(Category(slug="tent", name="Tienda"))
    category = Category(slug="camp", name="  tienda  ")

    with pytest.raises(DomainValidationError):
        save_category(category)

    assert category.name == "tienda"
    assert category.pk is None


@pytest.mark.django_db
def test_slug_of_a_saved_category_cannot_change():
    category = save_category(Category(slug="garden", name=GARDEN))
    category.slug = "yard"

    with pytest.raises(DomainValidationError) as raised:
        save_category(category)

    assert codes_of(raised) == {"slug": {"slug_immutable"}}
    assert Category.objects.get(pk=category.pk).slug == "garden"
    assert not Category.objects.filter(slug="yard").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "new_slug", ["Bad Slug", "tent", "a" * 51], ids=["format", "taken", "long"]
)
def test_changed_slug_reports_only_the_immutability(new_slug):
    save_category(Category(slug="tent", name="Tienda"))
    category = save_category(Category(slug="garden", name=GARDEN))
    category.slug = new_slug

    with pytest.raises(DomainValidationError) as raised:
        save_category(category)

    assert codes_of(raised) == {"slug": {"slug_immutable"}}


@pytest.mark.django_db
def test_changed_slug_and_name_errors_are_reported_together():
    category = save_category(Category(slug="garden", name=GARDEN))
    category.slug = "yard"
    category.name = "   "

    with pytest.raises(DomainValidationError) as raised:
        save_category(category)

    assert codes_of(raised) == {
        "slug": {"slug_immutable"},
        "name": {"name_empty"},
    }


@pytest.mark.django_db
def test_renaming_a_saved_category_is_accepted():
    category = save_category(Category(slug="garden", name=GARDEN))
    category.name = "Huerto"

    save_category(category)

    assert Category.objects.get(pk=category.pk).name == "Huerto"
    assert Category.objects.get(pk=category.pk).slug == "garden"


@pytest.mark.django_db
def test_saving_a_saved_category_without_changes_is_accepted():
    category = save_category(Category(slug="garden", name=GARDEN))

    save_category(category)

    assert stored("garden").name == GARDEN


@pytest.mark.django_db
def test_renaming_a_deleted_category_fails_instead_of_reinserting_it():
    category = save_category(Category(slug="garden", name=GARDEN))
    Category.objects.filter(pk=category.pk).delete()
    category.name = "Huerto"

    with pytest.raises(DatabaseError) as raised:
        save_category(category)

    assert str(raised.value) == "Save with update_fields did not affect any rows."
    assert not Category.objects.filter(pk=category.pk).exists()


def test_unknown_constraint_is_reported_without_details():
    assert services._codes_for_constraint("other_constraint") == {
        "__all__": ["constraint_violated"]
    }


@pytest.mark.django_db
def test_integrity_error_without_details_is_not_swallowed(monkeypatch):
    def fail(self, *args, **kwargs):
        raise IntegrityError("sin diagnóstico")

    monkeypatch.setattr(Category, "save", fail)

    with pytest.raises(DomainValidationError) as raised:
        save_category(Category(slug="garden", name=GARDEN))

    assert raised.value.message_dict == {"__all__": ["constraint_violated"]}


def test_error_codes_match_the_plan_table():
    assert services.ERROR_CODES == PLAN_ERROR_CODES
