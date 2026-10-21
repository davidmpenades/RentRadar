import pytest
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from apps.core.errors import DomainValidationError, translate_validation_error

SENTINEL = "SECRET_SENTINEL_VALUE"


def test_domain_error_message_dict_has_only_fields_and_codes():
    error = DomainValidationError(
        {"email": ["email_taken", "email_invalid"], "password": ["password_required"]}
    )

    assert error.message_dict == {
        "email": ["email_taken", "email_invalid"],
        "password": ["password_required"],
    }


def test_domain_error_keeps_each_code_as_message_and_code_without_params():
    error = DomainValidationError({"email": ["email_taken"]})

    (inner,) = error.error_dict["email"]
    assert inner.message == "email_taken"
    assert inner.code == "email_taken"
    assert inner.params is None


def test_domain_error_text_contains_only_fields_and_codes():
    error = DomainValidationError({"email": ["email_taken"]})

    assert SENTINEL not in str(error)
    assert SENTINEL not in repr(error)
    assert "email" in str(error)
    assert "email_taken" in str(error)
    assert "email_taken" in repr(error)


def test_domain_error_is_a_validation_error():
    assert issubclass(DomainValidationError, ValidationError)


def test_translate_maps_each_field_and_code_pair():
    error = ValidationError(
        {
            "email": [
                ValidationError("x", code="unique"),
                ValidationError("y", code="invalid"),
            ],
            "password": [ValidationError("z", code="max_length")],
        }
    )
    codes = {
        ("email", "unique"): "email_taken",
        ("email", "invalid"): "email_invalid",
        ("password", "max_length"): "password_too_long",
    }

    assert translate_validation_error(error, codes) == {
        "email": ["email_taken", "email_invalid"],
        "password": ["password_too_long"],
    }


def test_translate_discards_messages_and_params():
    error = ValidationError(
        {
            "email": [
                ValidationError(
                    f"El valor {SENTINEL} ya existe",
                    code="unique",
                    params={"value": SENTINEL},
                ),
            ]
        }
    )

    result = translate_validation_error(error, {("email", "unique"): "email_taken"})

    assert result == {"email": ["email_taken"]}
    assert SENTINEL not in repr(result)


def test_translate_removes_duplicates_keeping_order():
    error = ValidationError(
        {
            "email": [
                ValidationError("a", code="invalid"),
                ValidationError("b", code="max_length"),
                ValidationError("c", code="invalid"),
            ]
        }
    )
    codes = {
        ("email", "invalid"): "email_invalid",
        ("email", "max_length"): "email_too_long",
    }

    assert translate_validation_error(error, codes) == {
        "email": ["email_invalid", "email_too_long"]
    }


def test_translate_removes_duplicates_from_different_django_codes_with_same_target():
    error = ValidationError(
        {
            "email": [
                ValidationError("a", code="unique"),
                ValidationError("b", code="unique_together"),
            ]
        }
    )
    codes = {
        ("email", "unique"): "email_taken",
        ("email", "unique_together"): "email_taken",
    }

    assert translate_validation_error(error, codes) == {"email": ["email_taken"]}


def test_translate_sends_unmapped_pairs_to_validation_failed():
    error = ValidationError(
        {
            "email": [
                ValidationError(SENTINEL, code="surprise", params={"value": SENTINEL})
            ],
            NON_FIELD_ERRORS: [ValidationError(SENTINEL, code="other")],
        }
    )

    result = translate_validation_error(error, {})

    assert result == {"__all__": ["validation_failed"]}
    assert SENTINEL not in repr(result)


def test_translate_keeps_mapped_codes_next_to_unmapped_ones():
    error = ValidationError(
        {
            "email": [
                ValidationError("a", code="unique"),
                ValidationError("b", code="surprise"),
            ],
        }
    )

    assert translate_validation_error(error, {("email", "unique"): "email_taken"}) == {
        "email": ["email_taken"],
        "__all__": ["validation_failed"],
    }


@pytest.mark.parametrize("field", [NON_FIELD_ERRORS, "email"])
def test_translate_empty_error_dict_gives_empty_result(field):
    assert translate_validation_error(ValidationError({field: []}), {}) == {}
