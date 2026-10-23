import pytest
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import DataError, IntegrityError, transaction
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from apps.categories.models import Category
from apps.core.text import reject_control_characters

SLUG_KEY = "categories_category_slug_key"
NAME_LOWER_UNIQUE = "categories_category_name_lower_unique"
SLUG_PATTERN = r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z"
# Letra con tilde compuesta (NFC): cuenta como un carácter
ACCENTED = "é"


def format_errors(slug):
    # Sin BD: solo el formato y la longitud del campo, no la unicidad
    category = Category(slug=slug, name="Jardín")
    with pytest.raises(ValidationError) as raised:
        category.full_clean(
            exclude={"name"}, validate_unique=False, validate_constraints=False
        )
    return [error.code for error in raised.value.error_dict["slug"]]


def test_slug_field_definition():
    field = Category._meta.get_field("slug")

    assert field.unique is True
    assert field.blank is False
    assert field.max_length == 50
    (validator,) = [v for v in field.validators if isinstance(v, RegexValidator)]
    assert validator.regex.pattern == SLUG_PATTERN
    assert validator.code == "invalid"


def test_name_field_definition():
    field = Category._meta.get_field("name")

    assert field.blank is False
    assert field.max_length == 60
    assert reject_control_characters in field.validators


def test_name_uniqueness_ignores_case_with_a_named_constraint():
    (constraint,) = Category._meta.constraints

    assert isinstance(constraint, UniqueConstraint)
    assert constraint.expressions == (Lower("name"),)
    assert constraint.name == NAME_LOWER_UNIQUE
    assert constraint.violation_error_code == "name_taken"


def test_str_is_the_name():
    assert str(Category(slug="garden", name="Jardín")) == "Jardín"


@pytest.mark.parametrize("slug", ["ebike", "e-bike-2", "a", "a" * 50])
def test_slug_with_valid_format_passes_validation(slug):
    category = Category(slug=slug, name="Jardín")

    category.full_clean(
        exclude={"name"}, validate_unique=False, validate_constraints=False
    )


@pytest.mark.parametrize(
    "slug",
    [
        "Ebike",
        "e bike",
        "-ebike",
        "ebike-",
        "e--bike",
        "e_bike",
        "ebike\n",
        "e٣",
    ],
    ids=[
        "uppercase",
        "space",
        "leading-hyphen",
        "trailing-hyphen",
        "double-hyphen",
        "underscore",
        "trailing-newline",
        "arabic-indic-digit",
    ],
)
def test_slug_with_invalid_format_is_rejected(slug):
    assert format_errors(slug) == ["invalid"]


def test_empty_slug_is_blank_not_invalid():
    assert format_errors("") == ["blank"]


@pytest.mark.django_db
def test_slug_of_50_and_name_of_60_characters_are_saved():
    slug = "a" * 50
    name = ACCENTED * 60

    Category(slug=slug, name=name).save()

    assert Category.objects.filter(slug=slug, name=name).exists()


@pytest.mark.django_db
def test_slug_of_51_characters_is_rejected_by_the_database():
    with pytest.raises(DataError), transaction.atomic():
        Category(slug="a" * 51, name="Tienda").save()


@pytest.mark.django_db
def test_name_of_61_characters_is_rejected_by_the_database():
    with pytest.raises(DataError), transaction.atomic():
        Category(slug="tent", name=ACCENTED * 61).save()


@pytest.mark.django_db
def test_repeated_slug_is_rejected_by_the_database():
    Category(slug="garden", name="Jardín").save()

    with pytest.raises(IntegrityError) as raised, transaction.atomic():
        Category(slug="garden", name="Tienda").save()

    assert raised.value.__cause__.diag.constraint_name == SLUG_KEY


@pytest.mark.django_db
@pytest.mark.parametrize("other", ["TIENDA", "tienda"])
def test_names_differing_only_in_case_are_rejected_by_the_database(other):
    Category(slug="tent", name="Tienda").save()

    with pytest.raises(IntegrityError) as raised, transaction.atomic():
        Category(slug="camp", name=other).save()

    assert raised.value.__cause__.diag.constraint_name == NAME_LOWER_UNIQUE
