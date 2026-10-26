from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from apps.categories.models import Category
from apps.core.db import CONSTRAINT_VIOLATED, run_guarded
from apps.core.errors import (
    UNMAPPED_ERROR,
    DomainValidationError,
    translate_validation_error,
)

SLUG_EMPTY = "slug_empty"
SLUG_INVALID = "slug_invalid"
SLUG_TOO_LONG = "slug_too_long"
SLUG_TAKEN = "slug_taken"
SLUG_IMMUTABLE = "slug_immutable"
NAME_EMPTY = "name_empty"
NAME_INVALID = "name_invalid"
NAME_CONTROL_CHAR = "name_control_char"
NAME_TOO_LONG = "name_too_long"
NAME_TAKEN = "name_taken"
VALIDATION_FAILED = UNMAPPED_ERROR[1]

ERROR_CODES = frozenset(
    {
        SLUG_EMPTY,
        SLUG_INVALID,
        SLUG_TOO_LONG,
        SLUG_TAKEN,
        SLUG_IMMUTABLE,
        NAME_EMPTY,
        NAME_INVALID,
        NAME_CONTROL_CHAR,
        NAME_TOO_LONG,
        NAME_TAKEN,
        CONSTRAINT_VIOLATED,
        VALIDATION_FAILED,
    }
)

# (campo, código de Django) -> (campo, código de dominio)
DJANGO_CODES = {
    ("slug", "blank"): ("slug", SLUG_EMPTY),
    ("slug", "invalid"): ("slug", SLUG_INVALID),
    ("slug", "max_length"): ("slug", SLUG_TOO_LONG),
    ("slug", "unique"): ("slug", SLUG_TAKEN),
    ("name", "blank"): ("name", NAME_EMPTY),
    ("name", "control_char"): ("name", NAME_CONTROL_CHAR),
    ("name", "max_length"): ("name", NAME_TOO_LONG),
    (NON_FIELD_ERRORS, NAME_TAKEN): ("name", NAME_TAKEN),
}

CONSTRAINT_CODES = {
    "categories_category_slug_key": ("slug", SLUG_TAKEN),
    "categories_category_name_lower_unique": ("name", NAME_TAKEN),
}


def save_category(category):
    errors = {}
    exclude = set()
    if not isinstance(category.slug, str):
        errors["slug"] = [SLUG_INVALID]
        exclude.add("slug")
    if isinstance(category.name, str):
        category.name = Category.normalize_name(category.name)
    else:
        errors["name"] = [NAME_INVALID]
        exclude.add("name")
    if _slug_changed(category):
        errors["slug"] = [SLUG_IMMUTABLE]
        exclude.add("slug")
    errors.update(_validation_errors(category, exclude=exclude))
    if not errors:
        update_fields = None if category._state.adding else ["name"]
        _, errors = run_guarded(
            lambda: category.save(update_fields=update_fields), CONSTRAINT_CODES
        )
    if errors:
        raise DomainValidationError(errors)
    return category


def _slug_changed(category):
    if category._state.adding or not isinstance(category.slug, str):
        return False
    stored = (
        Category.objects.filter(pk=category.pk).values_list("slug", flat=True).first()
    )
    return stored is not None and stored != category.slug


def _validation_errors(category, *, exclude):
    try:
        category.full_clean(exclude=exclude)
    except ValidationError as exc:
        return translate_validation_error(exc, DJANGO_CODES)
    return {}
