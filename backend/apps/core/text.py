import unicodedata

from django.core.exceptions import ValidationError


def contains_control_character(text: str) -> bool:
    return any(unicodedata.category(char) == "Cc" for char in text)


def reject_control_characters(value: str) -> None:
    # Sin params: el valor recibido no debe viajar en el error
    if contains_control_character(value):
        raise ValidationError("control_char", code="control_char")
