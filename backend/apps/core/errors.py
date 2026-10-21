from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

UNMAPPED_ERROR = (NON_FIELD_ERRORS, "validation_failed")


class DomainValidationError(ValidationError):
    # Cada mensaje es el propio código y no lleva params: nunca guarda el valor recibido
    def __init__(self, codes_by_field: dict[str, list[str]]):
        super().__init__(
            {
                field: [ValidationError(code, code=code) for code in codes]
                for field, codes in codes_by_field.items()
            }
        )


def translate_validation_error(
    error: ValidationError, codes: dict[tuple[str, str], str]
) -> dict[str, list[str]]:
    translated: dict[str, list[str]] = {}
    for field, field_errors in error.error_dict.items():
        for field_error in field_errors:
            mapped_code = codes.get((field, field_error.code))
            target_field, target_code = (
                (field, mapped_code) if mapped_code else UNMAPPED_ERROR
            )
            target_codes = translated.setdefault(target_field, [])
            if target_code not in target_codes:
                target_codes.append(target_code)
    return translated
