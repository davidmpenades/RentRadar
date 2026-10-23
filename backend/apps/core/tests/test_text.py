import pytest
from django.core.exceptions import ValidationError

from apps.core.text import contains_control_character, reject_control_characters


@pytest.mark.parametrize(
    "text",
    ["a\x00b", "a\tb", "a\nb", "a\x01b", "a\x7fb", "\x00"],
    ids=["nul", "inner-tab", "newline", "x01", "del", "only-nul"],
)
def test_detects_control_characters(text):
    assert contains_control_character(text) is True


@pytest.mark.parametrize(
    "text",
    ["", "ana@correo.es", "Jardín", "a\u00a0b", "ñandú ☃"],
    ids=["empty", "plain", "accents", "nbsp", "unicode"],
)
def test_ignores_text_without_control_characters(text):
    assert contains_control_character(text) is False


def test_validator_accepts_clean_text():
    reject_control_characters("Jardín")


def test_validator_raises_control_char_without_params():
    with pytest.raises(ValidationError) as excinfo:
        reject_control_characters("a\x00b")

    error = excinfo.value
    assert error.code == "control_char"
    assert error.message == "control_char"
    assert error.params is None
