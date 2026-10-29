import math
from decimal import Decimal

import pytest

from apps.assets.rules import (
    STATUSES_ON_CREATE,
    STATUSES_ON_UPDATE,
    clean_currency,
    clean_description,
    clean_location,
    clean_price,
    clean_price_unit,
    clean_privacy_radius,
    clean_reference,
    clean_status,
    clean_title,
)

NULL = chr(0)
ESCAPE = chr(0x1B)
VERTICAL_TAB = chr(0x0B)
UNIT_SEPARATOR = chr(0x1F)
ZERO_WIDTH_JOINER = chr(0x200D)
RIGHT_TO_LEFT_OVERRIDE = chr(0x202E)
LONE_SURROGATE = chr(0xD800)
ACUTE_ACCENT = chr(0x301)
E_ACUTE = chr(0xE9)
FAMILY = (
    chr(0x1F468) + ZERO_WIDTH_JOINER + chr(0x1F469) + ZERO_WIDTH_JOINER + chr(0x1F467)
)
ARABIC_INDIC_ONE = chr(0x661)

NOT_TEXT = [None, 5, b"abc", ["abc"]]
LISBON = (38.7223, -9.1393)
ANDORRA = (42.5063, 1.5218)
TOULOUSE = (43.6047, 1.4442)
BOX_LIMITS = [(27.5, 0.0), (44.0, 0.0), (35.0, -18.5), (35.0, 5.0)]
BEYOND_BOX_LIMITS = [
    (math.nextafter(27.5, -math.inf), 0.0),
    (math.nextafter(44.0, math.inf), 0.0),
    (35.0, math.nextafter(-18.5, -math.inf)),
    (35.0, math.nextafter(5.0, math.inf)),
]
RANGE_LIMITS = [(90.0, 0.0), (-90.0, 0.0), (0.0, 180.0), (0.0, -180.0)]
BEYOND_RANGE_LIMITS = [
    (math.nextafter(90.0, math.inf), 0.0),
    (math.nextafter(-90.0, -math.inf), 0.0),
    (0.0, math.nextafter(180.0, math.inf)),
    (0.0, math.nextafter(-180.0, -math.inf)),
    (91.0, 3.0),
    (-91.0, 3.0),
    (40.0, 181.0),
    (40.0, -181.0),
]
INVALID_COORDINATES = [
    (True, 3.0),
    (40.0, False),
    ("40.4", 3.0),
    (40.0, "3"),
    (None, 3.0),
    (40.0, None),
    (b"40", 3.0),
    (math.nan, 3.0),
    (40.0, math.inf),
    (-math.inf, 3.0),
    (10**400, 3.0),
    (40.0, -(10**400)),
    (Decimal("NaN"), 3.0),
    (Decimal("sNaN"), 3.0),
    (Decimal("Infinity"), 3.0),
    (Decimal("1E+400"), 3.0),
    (math.nan, 999.0),
    (999.0, math.nan),
]
REFERENCE_CODES = [
    ("owner", "owner_invalid"),
    ("category", "category_invalid"),
    ("asset", "asset_not_found"),
]
DESCRIPTION = "Taladro de percusion en buen estado"
INVALID_REFERENCES = [None, True, False, "5", 5.0, 0, -1, 2**63, [1]]


@pytest.mark.parametrize("raw", ["  Taladro  ", "Taladro"])
def test_a_valid_title_is_returned_trimmed(raw):
    assert clean_title(raw) == ("Taladro", [])


@pytest.mark.parametrize("length", [3, 100])
def test_titles_of_three_to_one_hundred_characters_are_accepted(length):
    assert clean_title("a" * length) == ("a" * length, [])


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("ab", "title_too_short"),
        ("a" * 101, "title_too_long"),
        ("   ", "title_too_short"),
        ("a b", "title_too_short"),
        (ZERO_WIDTH_JOINER * 3, "title_too_short"),
        ("a" + ZERO_WIDTH_JOINER * 2, "title_too_short"),
        ("abc" + RIGHT_TO_LEFT_OVERRIDE, "title_format_char"),
        ("ab" + RIGHT_TO_LEFT_OVERRIDE + "c", "title_format_char"),
        ("ab" + NULL + "c", "title_control_char"),
        ("ab\nc", "title_control_char"),
        ("ab" + ESCAPE + "c", "title_control_char"),
        ("ab" + UNIT_SEPARATOR + "c", "title_control_char"),
    ],
)
def test_a_title_with_one_problem_gets_that_code(raw, code):
    assert clean_title(raw) == (None, [code])


def test_a_title_with_several_problems_gets_all_codes_in_order():
    assert clean_title("a" + NULL + RIGHT_TO_LEFT_OVERRIDE) == (
        None,
        ["title_control_char", "title_format_char", "title_too_short"],
    )
    assert clean_title("x" * 101 + NULL) == (
        None,
        ["title_control_char", "title_too_long"],
    )


@pytest.mark.parametrize("raw", NOT_TEXT + ["abc" + LONE_SURROGATE])
def test_a_title_that_is_not_valid_text_is_invalid(raw):
    assert clean_title(raw) == (None, ["title_invalid"])


def test_a_composed_emoji_counts_each_emoji_and_not_the_joiners():
    assert clean_title(FAMILY) == (FAMILY, [])


def test_a_title_is_normalised_before_it_is_measured():
    assert clean_title("Caf" + "e" + ACUTE_ACCENT) == ("Caf" + E_ACUTE, [])
    assert clean_title(("e" + ACUTE_ACCENT) * 100) == (E_ACUTE * 100, [])
    assert clean_title(("e" + ACUTE_ACCENT) * 101) == (None, ["title_too_long"])


@pytest.mark.parametrize("edge", [UNIT_SEPARATOR, VERTICAL_TAB])
def test_a_control_character_that_is_whitespace_is_trimmed_at_the_edges(edge):
    assert clean_title("abc" + edge) == ("abc", [])
    assert clean_title(edge + "abc") == ("abc", [])


@pytest.mark.parametrize("length", [20, 2000])
def test_descriptions_of_twenty_to_two_thousand_characters_are_accepted(length):
    assert clean_description("a" * length) == ("a" * length, [])


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("a" * 19, "description_too_short"),
        ("a" * 2001, "description_too_long"),
        (DESCRIPTION + ESCAPE, "description_control_char"),
        (DESCRIPTION + NULL + "x", "description_control_char"),
        (DESCRIPTION + RIGHT_TO_LEFT_OVERRIDE + "x", "description_format_char"),
    ],
)
def test_a_description_with_one_problem_gets_that_code(raw, code):
    assert clean_description(raw) == (None, [code])


def test_a_description_counts_code_points_and_not_visible_characters():
    raw = "a" + " " * 18 + "b"
    assert clean_description(raw) == (raw, [])


@pytest.mark.parametrize("raw", [DESCRIPTION + "\r\n" + DESCRIPTION, "a\tb" * 10])
def test_a_description_admits_line_breaks_and_tabs(raw):
    assert clean_description(raw) == (raw, [])


def test_a_description_is_returned_trimmed_and_normalised():
    assert clean_description("  " + "e" + ACUTE_ACCENT + "a" * 19 + "\n") == (
        E_ACUTE + "a" * 19,
        [],
    )


def test_a_description_admits_a_composed_emoji():
    assert clean_description("a" * 20 + FAMILY) == ("a" * 20 + FAMILY, [])


@pytest.mark.parametrize("raw", NOT_TEXT + [DESCRIPTION + LONE_SURROGATE])
def test_a_description_that_is_not_valid_text_is_invalid(raw):
    assert clean_description(raw) == (None, ["description_invalid"])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0.01", "0.01"),
        ("99999.99", "99999.99"),
        ("12.340", "12.34"),
        ("12.5", "12.50"),
        ("+5", "5.00"),
        ("007.50", "7.50"),
        (".5", "0.50"),
        ("5.", "5.00"),
        (Decimal("12.5"), "12.50"),
        (Decimal("12.340"), "12.34"),
    ],
)
def test_a_valid_price_is_returned_with_two_decimals(raw, expected):
    value, codes = clean_price(raw)
    assert codes == []
    assert isinstance(value, Decimal)
    assert str(value) == expected


@pytest.mark.parametrize(
    "raw",
    [
        0.1,
        True,
        False,
        5,
        None,
        b"5",
        [5],
        "",
        "+",
        ".",
        "1.2.3",
        "0x10",
        "1e2",
        "1E2",
        "NaN",
        "Infinity",
        "-Infinity",
        "sNaN",
        "12,50",
        " 5",
        "5 ",
        "5\n",
        "1_0",
        ARABIC_INDIC_ONE,
        Decimal("1E+2"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("sNaN"),
    ],
)
def test_a_price_that_is_not_a_plain_decimal_is_invalid(raw):
    assert clean_price(raw) == (None, ["price_invalid"])


@pytest.mark.parametrize(
    ("raw", "codes"),
    [
        ("0", ["price_out_of_range"]),
        ("0.00", ["price_out_of_range"]),
        ("-5", ["price_out_of_range"]),
        ("100000", ["price_out_of_range"]),
        ("12.345", ["price_too_precise"]),
        ("12.3400000000000000000000000001", ["price_too_precise"]),
        ("0.001", ["price_out_of_range", "price_too_precise"]),
        ("100000.123", ["price_out_of_range", "price_too_precise"]),
    ],
)
def test_a_price_out_of_range_or_too_precise_gets_every_code_that_applies(raw, codes):
    assert clean_price(raw) == (None, codes)


def test_the_currency_is_euro():
    assert clean_currency("EUR") == ("EUR", [])


@pytest.mark.parametrize("raw", ["usd", "eur", "USD", "EUR ", "", None, 1])
def test_any_other_currency_is_invalid(raw):
    assert clean_currency(raw) == (None, ["currency_invalid"])


@pytest.mark.parametrize("raw", ["hour", "day", "week", "month"])
def test_the_four_price_units_are_accepted(raw):
    assert clean_price_unit(raw) == (raw, [])


@pytest.mark.parametrize("raw", ["night", "Day", "HOUR", "", None, 1, ["day"]])
def test_any_other_price_unit_is_invalid(raw):
    assert clean_price_unit(raw) == (None, ["price_unit_invalid"])


@pytest.mark.parametrize("raw", [500, 1000, 2000])
def test_the_three_privacy_radii_are_accepted(raw):
    assert clean_privacy_radius(raw) == (raw, [])


@pytest.mark.parametrize(
    "raw",
    [0, -500, 1500, 500.5, 500.0, True, False, "500", Decimal(500), None],
)
def test_any_other_privacy_radius_is_invalid(raw):
    assert clean_privacy_radius(raw) == (None, ["privacy_radius_invalid"])


def test_a_new_asset_can_only_be_paused():
    assert clean_status("paused", allowed=STATUSES_ON_CREATE) == ("paused", [])


@pytest.mark.parametrize("raw", ["active", "deleted", "Paused", "", None])
def test_any_other_status_on_creation_is_invalid(raw):
    assert clean_status(raw, allowed=STATUSES_ON_CREATE) == (None, ["status_invalid"])


@pytest.mark.parametrize("raw", ["active", "paused"])
def test_an_asset_can_be_active_or_paused_on_update(raw):
    assert clean_status(raw, allowed=STATUSES_ON_UPDATE) == (raw, [])


@pytest.mark.parametrize("raw", ["deleted", "Active", "", None])
def test_any_other_status_on_update_is_invalid(raw):
    assert clean_status(raw, allowed=STATUSES_ON_UPDATE) == (None, ["status_invalid"])


@pytest.mark.parametrize(
    "point", [(40.4168, -3.7038), LISBON, ANDORRA, TOULOUSE, *BOX_LIMITS]
)
def test_a_point_inside_the_coherence_box_is_accepted(point):
    assert clean_location(*point) == (point, [])


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(40, -3), (Decimal("40.4"), Decimal("-3.7")), (40.4, Decimal("-3.7"))],
)
def test_the_coordinates_come_back_as_floats(latitude, longitude):
    result, codes = clean_location(latitude, longitude)
    assert codes == []
    assert [type(value) for value in result] == [float, float]
    assert result == (float(latitude), float(longitude))


@pytest.mark.parametrize("point", [(-3.7, 40.4), *BEYOND_BOX_LIMITS])
def test_a_point_outside_the_coherence_box_is_rejected(point):
    assert clean_location(*point) == (None, ["location_outside_bounds"])


@pytest.mark.parametrize("point", RANGE_LIMITS)
def test_the_range_limits_are_included_and_fall_to_the_box_check(point):
    assert clean_location(*point) == (None, ["location_outside_bounds"])


@pytest.mark.parametrize("point", BEYOND_RANGE_LIMITS)
def test_a_coordinate_beyond_the_range_is_out_of_range(point):
    assert clean_location(*point) == (None, ["location_out_of_range"])


@pytest.mark.parametrize(("latitude", "longitude"), INVALID_COORDINATES)
def test_a_coordinate_that_is_not_a_finite_number_is_invalid(latitude, longitude):
    assert clean_location(latitude, longitude) == (None, ["location_invalid"])


@pytest.mark.parametrize("field", ["owner", "category", "asset"])
@pytest.mark.parametrize("raw", [1, 2**63 - 1])
def test_a_reference_in_range_is_accepted(field, raw):
    assert clean_reference(raw, field) == (raw, [])


@pytest.mark.parametrize(("field", "code"), REFERENCE_CODES)
@pytest.mark.parametrize("raw", INVALID_REFERENCES)
def test_an_invalid_reference_gets_the_code_of_its_field(field, code, raw):
    assert clean_reference(raw, field) == (None, [code])
