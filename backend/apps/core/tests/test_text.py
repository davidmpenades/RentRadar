import pytest
from django.core.exceptions import ValidationError

from apps.core.text import (
    contains_control_character,
    contains_lone_surrogate,
    reject_control_characters,
)

HIGH_SURROGATE = chr(0xD800)
LOW_SURROGATE = chr(0xDFFF)


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


@pytest.mark.parametrize(
    "text",
    [
        HIGH_SURROGATE,
        LOW_SURROGATE,
        "ana@" + HIGH_SURROGATE + ".es",
        "ana" + LOW_SURROGATE,
        LOW_SURROGATE + HIGH_SURROGATE,
    ],
    ids=["high", "low", "in-the-middle", "low-at-the-end", "reversed-pair"],
)
def test_detects_lone_surrogates(text):
    assert contains_lone_surrogate(text) is True


@pytest.mark.parametrize(
    "text",
    ["", "ana@correo.es", "Jardín", "ñandú ☃", chr(0x1F600), "a" + chr(0x1F600) + "b"],
    ids=["empty", "plain", "accents", "unicode", "emoji", "emoji-in-the-middle"],
)
def test_ignores_text_without_lone_surrogates(text):
    assert contains_lone_surrogate(text) is False
