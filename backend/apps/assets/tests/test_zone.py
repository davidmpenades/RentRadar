import ast
import copy
import dataclasses
from decimal import Decimal, getcontext, localcontext
from pathlib import Path

import pytest

from apps.assets import zone
from apps.assets.zone import (
    NOT_A_NUMBER,
    OUT_OF_RANGE,
    PARAMETER_CODES,
    REPEATED,
    REQUIRED,
    TOO_LONG,
    Zone,
    ZoneError,
    parse_zone,
)
from apps.core.api import ERROR_CODES

ARABIC_INDIC_ONE = chr(0x661)
FULLWIDTH_THREE = chr(0xFF13)
FULLWIDTH_NINE = chr(0xFF19)
SUPERSCRIPT_TWO = chr(0xB2)
MINUS_SIGN = chr(0x2212)
NO_BREAK_SPACE = chr(0xA0)
ZERO_WIDTH_SPACE = chr(0x200B)
PARAMETER_ORDER = ["south", "west", "north", "east"]

VALENCIA = {"south": "39.4", "west": "-0.4", "north": "39.5", "east": "-0.3"}
DECIMALS_32 = "39." + "1" * 29
DECIMALS_33 = "39." + "1" * 30
GARBAGE_33 = "x" * 33


def make_params(**overrides):
    values = {**VALENCIA, **overrides}
    return {
        name: value if isinstance(value, list) else [value]
        for name, value in values.items()
    }


def invalid(params):
    return ZoneError("invalid_parameters", params)


INVALID_TEXTS = [
    pytest.param("abc", id="letters"),
    pytest.param("", id="present_but_empty"),
    pytest.param(" ", id="only_a_space"),
    pytest.param("NaN", id="nan"),
    pytest.param("nan", id="nan_lowercase"),
    pytest.param("sNaN", id="signalling_nan"),
    pytest.param("Infinity", id="infinity"),
    pytest.param("-inf", id="negative_inf"),
    pytest.param("inf", id="inf"),
    pytest.param("1e1", id="exponent"),
    pytest.param("1E1", id="exponent_uppercase"),
    pytest.param("39,4", id="decimal_comma"),
    pytest.param(" 39.4", id="leading_space"),
    pytest.param("39.4 ", id="trailing_space"),
    pytest.param("39.4\n", id="trailing_newline"),
    pytest.param("\n39.4", id="leading_newline"),
    pytest.param("39.4\t", id="trailing_tab"),
    pytest.param("39.4" + chr(0), id="trailing_null"),
    pytest.param(NO_BREAK_SPACE + "39.4", id="leading_no_break_space"),
    pytest.param("39.4" + ZERO_WIDTH_SPACE, id="trailing_zero_width_space"),
    pytest.param(ARABIC_INDIC_ONE, id="arabic_indic_digit"),
    pytest.param(FULLWIDTH_THREE + FULLWIDTH_NINE + ".4", id="fullwidth_digits"),
    pytest.param("39.4" + SUPERSCRIPT_TWO, id="superscript_digit"),
    pytest.param("39." + ARABIC_INDIC_ONE, id="non_ascii_decimal_digit"),
    pytest.param(MINUS_SIGN + "39.4", id="unicode_minus_sign"),
    pytest.param("+39", id="plus_sign"),
    pytest.param("+0", id="plus_zero"),
    pytest.param("039", id="leading_zero"),
    pytest.param("00", id="double_zero"),
    pytest.param("-039", id="negative_leading_zero"),
    pytest.param("39.", id="trailing_point"),
    pytest.param(".5", id="no_integer_part"),
    pytest.param("-.5", id="negative_no_integer_part"),
    pytest.param("1_0", id="underscore"),
    pytest.param("-", id="only_a_sign"),
    pytest.param("--1", id="double_sign"),
    pytest.param("1.2.3", id="two_points"),
    pytest.param("0x10", id="hexadecimal"),
    pytest.param("39.4;", id="trailing_semicolon"),
]


@pytest.mark.parametrize("name", PARAMETER_ORDER)
@pytest.mark.parametrize("text", INVALID_TEXTS)
def test_text_that_is_not_a_plain_decimal_is_rejected_as_not_a_number(name, text):
    result = parse_zone(make_params(**{name: text}))

    assert result == invalid({name: NOT_A_NUMBER})


@pytest.mark.parametrize("name", PARAMETER_ORDER)
def test_missing_parameter_is_required(name):
    params = make_params()
    del params[name]

    assert parse_zone(params) == invalid({name: REQUIRED})


@pytest.mark.parametrize("name", PARAMETER_ORDER)
def test_empty_list_of_values_is_required(name):
    assert parse_zone(make_params(**{name: []})) == invalid({name: REQUIRED})


def test_present_but_empty_value_is_not_a_number_and_not_required():
    result = parse_zone(make_params(south=""))

    assert result == invalid({"south": NOT_A_NUMBER})


def test_empty_mapping_requires_the_four_bounds_in_order():
    result = parse_zone({})

    assert result == invalid({name: REQUIRED for name in PARAMETER_ORDER})
    assert list(result.params) == PARAMETER_ORDER


@pytest.mark.parametrize("name", PARAMETER_ORDER)
@pytest.mark.parametrize(
    "values",
    [
        pytest.param(["39.4", "39.5"], id="two_valid_values"),
        pytest.param(["39.4", "39.4"], id="same_value_twice"),
        pytest.param(["abc", "def"], id="two_invalid_values"),
        pytest.param(["", ""], id="two_empty_values"),
        pytest.param([GARBAGE_33, GARBAGE_33], id="two_values_too_long"),
        pytest.param(["1000", "2000"], id="two_values_out_of_range"),
        pytest.param(["39.4", "39.5", "39.6"], id="three_values"),
    ],
)
def test_repeated_parameter_is_rejected_whatever_its_values_are(name, values):
    assert parse_zone(make_params(**{name: values})) == invalid({name: REPEATED})


def test_value_of_33_characters_that_is_numerically_valid_is_too_long():
    assert len(DECIMALS_33) == 33

    result = parse_zone(make_params(south=DECIMALS_33))

    assert result == invalid({"south": TOO_LONG})


def test_value_of_33_characters_of_garbage_is_too_long_not_a_number():
    result = parse_zone(make_params(south=GARBAGE_33))

    assert result == invalid({"south": TOO_LONG})


def test_value_of_33_characters_out_of_range_is_too_long_not_out_of_range():
    value = "91." + "0" * 30
    assert len(value) == 33

    assert parse_zone(make_params(south=value)) == invalid({"south": TOO_LONG})


def test_value_of_32_characters_with_many_decimals_is_accepted_exactly():
    assert len(DECIMALS_32) == 32

    result = parse_zone(make_params(south=DECIMALS_32))

    assert isinstance(result, Zone)
    assert result.south == Decimal(DECIMALS_32)
    assert str(result.south) == DECIMALS_32


def test_very_long_value_is_too_long():
    assert parse_zone(make_params(east="1" * 10_000)) == invalid({"east": TOO_LONG})


@pytest.mark.parametrize(
    "name, value",
    [
        pytest.param("south", "90.000001", id="south_just_above_90"),
        pytest.param("north", "90.000001", id="north_just_above_90"),
        pytest.param("south", "-90.000001", id="south_just_below_minus_90"),
        pytest.param("north", "-90.000001", id="north_just_below_minus_90"),
        pytest.param(
            "south", "90.0000000000000000000000000001", id="south_beyond_28_digits"
        ),
        pytest.param(
            "north", "-90.0000000000000000000000000001", id="north_beyond_28_digits"
        ),
        pytest.param("south", "100", id="longitude_valid_value_as_latitude"),
        pytest.param("north", "-180", id="minus_180_as_latitude"),
        pytest.param("west", "-180.5", id="west_below_minus_180"),
        pytest.param("east", "180.000001", id="east_just_above_180"),
        pytest.param("west", "-180." + "0" * 26 + "1", id="west_beyond_28_digits"),
        pytest.param("east", "181", id="east_181"),
        pytest.param("east", "99999999999999999999999999999999", id="east_32_digits"),
    ],
)
def test_value_outside_its_limit_is_out_of_range(name, value):
    assert parse_zone(make_params(**{name: value})) == invalid({name: OUT_OF_RANGE})


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"south": "-90", "north": "-89.9"}, id="south_at_minus_90"),
        pytest.param({"south": "89.9", "north": "90"}, id="north_at_90"),
        pytest.param({"west": "-180", "east": "-179.9"}, id="west_at_minus_180"),
        pytest.param({"west": "179.9", "east": "180"}, id="east_at_180"),
        pytest.param({"south": "90", "north": "90"}, id="both_latitudes_at_90"),
        pytest.param({"south": "-90", "north": "-90"}, id="both_latitudes_at_minus_90"),
        pytest.param({"west": "180", "east": "180"}, id="both_longitudes_at_180"),
        pytest.param(
            {"west": "-180", "east": "-180"}, id="both_longitudes_at_minus_180"
        ),
        pytest.param(
            {"south": "-90.0", "north": "-89.900"}, id="minus_90_with_trailing_zeros"
        ),
    ],
)
def test_limits_of_90_and_180_are_inclusive(overrides):
    assert isinstance(parse_zone(make_params(**overrides)), Zone)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"west": "95", "east": "100"}, id="west_beyond_latitude_range"),
        pytest.param(
            {"west": "-130", "east": "-120.5"}, id="east_beyond_latitude_range"
        ),
    ],
)
def test_latitude_limit_does_not_apply_to_longitude_parameters(overrides):
    assert isinstance(parse_zone(make_params(**overrides)), Zone)


def test_south_and_east_failing_together_report_both_codes_and_no_zone_code():
    result = parse_zone(make_params(south="abc", east="181"))

    assert result == invalid({"south": NOT_A_NUMBER, "east": OUT_OF_RANGE})


def test_four_bounds_failing_with_different_codes_are_reported_in_fixed_order():
    params = {
        "east": ["abc"],
        "north": [GARBAGE_33],
        "west": ["1", "2"],
    }

    result = parse_zone(params)

    assert result == invalid(
        {"south": REQUIRED, "west": REPEATED, "north": TOO_LONG, "east": NOT_A_NUMBER}
    )
    assert list(result.params) == PARAMETER_ORDER


def test_out_of_range_is_reported_together_with_other_codes_in_fixed_order():
    params = {
        "east": ["181"],
        "north": ["abc"],
        "west": ["1", "2"],
        "south": ["91"],
    }

    result = parse_zone(params)

    assert list(result.params) == PARAMETER_ORDER
    assert result.params == {
        "south": OUT_OF_RANGE,
        "west": REPEATED,
        "north": NOT_A_NUMBER,
        "east": OUT_OF_RANGE,
    }


def test_every_parameter_code_can_be_produced():
    produced = set()
    cases = [
        make_params(south=[]),
        make_params(south=["1", "2"]),
        make_params(south=GARBAGE_33),
        make_params(south="abc"),
        make_params(south="91"),
    ]
    for case in cases:
        produced |= set(parse_zone(case).params.values())

    assert produced == PARAMETER_CODES


@pytest.mark.parametrize(
    "overrides, expected",
    [
        pytest.param(
            {"south": "50", "north": "10", "west": "abc"},
            {"west": NOT_A_NUMBER},
            id="inverted_latitudes_are_not_checked",
        ),
        pytest.param(
            {"west": "40", "east": "-40", "north": "91"},
            {"north": OUT_OF_RANGE},
            id="inverted_longitudes_are_not_checked",
        ),
        pytest.param(
            {"south": "-90", "north": "90", "west": "-180", "east": "180.5"},
            {"east": OUT_OF_RANGE},
            id="area_is_not_checked",
        ),
        pytest.param(
            {"south": "-90", "north": "90", "west": "-180", "east": []},
            {"east": REQUIRED},
            id="area_is_not_checked_when_a_bound_is_missing",
        ),
    ],
)
def test_invalid_bounds_report_only_parameter_codes(overrides, expected):
    assert parse_zone(make_params(**overrides)) == invalid(expected)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"south": "40", "north": "39"}, id="latitudes_inverted"),
        pytest.param({"west": "-0.3", "east": "-0.4"}, id="longitudes_inverted"),
        pytest.param({"west": "179", "east": "-179"}, id="across_the_antimeridian"),
        pytest.param({"south": "-89", "north": "-90"}, id="inverted_in_the_south"),
        pytest.param({"south": "0.1", "north": "0"}, id="inverted_by_a_tenth"),
        pytest.param(
            {"south": "10." + "0" * 27 + "1", "north": "10"},
            id="inverted_beyond_28_digits",
        ),
        pytest.param(
            {"west": "-179.9999999999999999999999999", "east": "-180"},
            id="longitudes_inverted_beyond_26_digits",
        ),
    ],
)
def test_inverted_zone_is_rejected_as_zone_inverted(overrides):
    assert parse_zone(make_params(**overrides)) == ZoneError("zone_inverted", {})


def test_inverted_zone_with_both_axes_inverted_and_positive_area_is_only_inverted():
    params = make_params(south="50", north="10", west="40", east="-40")
    assert (-40 - 40) * (10 - 50) > 6

    assert parse_zone(params) == ZoneError("zone_inverted", {})


def test_inverted_zone_with_a_huge_negative_area_is_only_inverted():
    params = make_params(south="50", north="-50", west="-100", east="100")

    assert parse_zone(params) == ZoneError("zone_inverted", {})


def test_negative_zero_south_with_zero_north_is_not_inverted():
    result = parse_zone(make_params(south="-0", north="0"))

    assert isinstance(result, Zone)


def test_equal_latitudes_are_a_valid_zone_with_zero_area():
    result = parse_zone(make_params(south="39.4", north="39.4"))

    assert result == Zone(
        Decimal("39.4"), Decimal("-0.4"), Decimal("39.4"), Decimal("-0.3")
    )


def test_equal_longitudes_are_a_valid_zone_with_zero_area():
    result = parse_zone(make_params(west="-0.4", east="-0.4"))

    assert isinstance(result, Zone)


def test_single_point_zone_is_valid():
    params = make_params(south="39.4", north="39.4", west="-0.4", east="-0.4")

    assert isinstance(parse_zone(params), Zone)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {"south": "0", "north": "2", "west": "0", "east": "3"}, id="two_by_three"
        ),
        pytest.param(
            {"south": "0", "north": "3", "west": "0", "east": "2"}, id="three_by_two"
        ),
        pytest.param(
            {"south": "0", "north": "2.000", "west": "0.0", "east": "3.00"},
            id="two_by_three_with_trailing_zeros",
        ),
        pytest.param(
            {"south": "0", "north": "0.1", "west": "0.1", "east": "60.1"},
            id="tenth_by_sixty_without_float_error",
        ),
        pytest.param(
            {"south": "-1", "north": "1", "west": "-1.5", "east": "1.5"},
            id="centred_on_the_origin",
        ),
    ],
)
def test_area_of_exactly_6_is_accepted(overrides):
    assert isinstance(parse_zone(make_params(**overrides)), Zone)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {"south": "10", "north": "12", "west": "20", "east": "23.00005"},
            id="width_over_by_a_hundred_thousandth",
        ),
        pytest.param(
            {"south": "0", "north": "2.00004", "west": "0", "east": "3"},
            id="height_over_by_a_hundred_thousandth",
        ),
        pytest.param(
            {"south": "0", "north": "1", "west": "0", "east": "6.0001"},
            id="one_high_and_six_and_a_ten_thousandth_wide",
        ),
        pytest.param(
            {"south": "-90", "north": "90", "west": "-180", "east": "180"}, id="world"
        ),
    ],
)
def test_area_above_6_is_rejected_as_zone_too_large(overrides):
    assert parse_zone(make_params(**overrides)) == ZoneError("zone_too_large", {})


def test_area_of_6_with_a_31_character_tail_is_rejected_by_exact_arithmetic():
    height = "2.00000000000000000000000000001"
    assert len(height) == 31
    params = make_params(south="0", north=height, west="0", east="3")

    assert parse_zone(params) == ZoneError("zone_too_large", {})


def test_area_slightly_below_6_with_a_long_tail_is_accepted():
    height = "1.99999999999999999999999999999"
    params = make_params(south="0", north=height, west="0", east="3")

    assert isinstance(parse_zone(params), Zone)


def test_valid_zone_returns_exact_decimals_in_a_zone():
    params = make_params(
        south="39.4699999999999999999",
        west="-0.40",
        north="39.4700000000000000001",
        east="-0.3763",
    )

    result = parse_zone(params)

    assert result == Zone(
        Decimal("39.4699999999999999999"),
        Decimal("-0.40"),
        Decimal("39.4700000000000000001"),
        Decimal("-0.3763"),
    )
    assert [type(value) for value in dataclasses.astuple(result)] == [Decimal] * 4
    assert str(result.south) == "39.4699999999999999999"
    assert str(result.west) == "-0.40"
    assert str(result.north) == "39.4700000000000000001"
    assert str(result.east) == "-0.3763"


def test_zone_keeps_each_bound_in_its_own_field():
    result = parse_zone(make_params(south="1", west="2", north="3", east="4"))

    assert (result.south, result.west, result.north, result.east) == (
        Decimal(1),
        Decimal(2),
        Decimal(3),
        Decimal(4),
    )


def test_negative_zero_is_accepted_as_a_bound():
    result = parse_zone(make_params(south="-0", north="1", west="-0", east="1"))

    assert isinstance(result, Zone)
    assert result.south == 0
    assert result.west == 0


def test_unknown_parameters_are_ignored():
    params = make_params()
    params["radius"] = ["abc"]
    params["page"] = []
    params["extra"] = ["1", "2"]

    assert parse_zone(params) == parse_zone(make_params())
    assert isinstance(parse_zone(params), Zone)


def test_parameter_names_are_case_sensitive():
    params = make_params()
    params["South"] = params.pop("south")

    assert parse_zone(params) == invalid({"south": REQUIRED})


def test_error_params_never_contain_the_received_value():
    result = parse_zone(make_params(south="secret-value"))

    assert "secret-value" not in repr(result)


@pytest.mark.parametrize(
    "params",
    [
        pytest.param(make_params(), id="valid"),
        pytest.param(make_params(south="abc"), id="invalid_parameter"),
        pytest.param(make_params(south="50", north="10"), id="inverted"),
        pytest.param(make_params(east="180", west="-180"), id="too_large"),
    ],
)
def test_parse_zone_does_not_modify_its_input(params):
    snapshot = copy.deepcopy(params)

    parse_zone(params)

    assert params == snapshot


def test_zone_is_immutable():
    result = parse_zone(make_params())

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.south = Decimal(0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.extra = 1


def test_zone_error_is_immutable():
    result = parse_zone(make_params(south="abc"))

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.code = "zone_inverted"


def test_area_is_exact_even_if_the_global_context_has_the_default_precision():
    height = "2.00000000000000000000000000001"

    with localcontext() as context:
        context.prec = 28
        result = parse_zone(make_params(south="0", north=height, west="0", east="3"))

    assert result == ZoneError("zone_too_large", {})


def test_parse_zone_gives_the_same_answers_with_a_context_of_few_digits():
    height = "2.00000000000000000000000000001"

    with localcontext() as context:
        context.prec = 3
        too_large = parse_zone(make_params(south="0", north=height, west="0", east="3"))
        inverted = parse_zone(make_params(south="10.0001", north="10"))
        too_long = parse_zone(make_params(south=DECIMALS_33))

    assert too_large == ZoneError("zone_too_large", {})
    assert inverted == ZoneError("zone_inverted", {})
    assert too_long == invalid({"south": TOO_LONG})


def test_bounds_beyond_the_context_precision_are_compared_exactly():
    with localcontext() as context:
        context.prec = 3
        result = parse_zone(make_params(south="90.0000001"))

    assert result == invalid({"south": OUT_OF_RANGE})


@pytest.mark.parametrize(
    "params",
    [
        pytest.param(make_params(), id="valid"),
        pytest.param(
            make_params(
                south="0", north="2.00000000000000000000000000001", west="0", east="3"
            ),
            id="too_large",
        ),
        pytest.param(make_params(south="50", north="10"), id="inverted"),
        pytest.param(make_params(south="abc"), id="invalid_parameter"),
    ],
)
def test_parse_zone_leaves_the_global_decimal_context_untouched(params):
    before = repr(getcontext())

    parse_zone(params)

    assert repr(getcontext()) == before


def test_global_decimal_context_has_the_default_precision_during_the_tests():
    assert getcontext().prec == 28


def test_parameter_codes_are_exactly_the_five_of_the_error_table():
    codes = {"required", "repeated", "too_long", "not_a_number", "out_of_range"}

    assert set(PARAMETER_CODES) == codes
    assert isinstance(PARAMETER_CODES, frozenset)


def test_parameter_code_constants_hold_plain_text():
    for constant in (REQUIRED, REPEATED, TOO_LONG, NOT_A_NUMBER, OUT_OF_RANGE):
        assert type(constant) is str


def test_general_error_codes_are_known_to_the_api_error_table():
    assert {
        "invalid_parameters",
        "zone_inverted",
        "zone_too_large",
    } <= ERROR_CODES


@pytest.mark.parametrize(
    "params, code",
    [
        pytest.param(
            make_params(south="abc"), "invalid_parameters", id="invalid_parameters"
        ),
        pytest.param(
            make_params(south="50", north="10"), "zone_inverted", id="zone_inverted"
        ),
        pytest.param(
            make_params(west="-180", east="180"), "zone_too_large", id="zone_too_large"
        ),
    ],
)
def test_every_error_code_returned_belongs_to_the_api_error_table(params, code):
    result = parse_zone(params)

    assert result.code == code
    assert result.code in ERROR_CODES


def test_codes_without_parameters_carry_an_empty_params_dict():
    assert parse_zone(make_params(south="50", north="10")).params == {}
    assert parse_zone(make_params(west="-180", east="180")).params == {}


def test_every_parameter_code_returned_belongs_to_the_parameter_codes():
    result = parse_zone({"east": ["abc"], "west": ["1", "2"]})

    assert set(result.params.values()) <= PARAMETER_CODES


def test_zone_module_stays_pure_without_django_drf_or_other_apps():
    tree = ast.parse(Path(zone.__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "sin imports relativos"
            imported.append(node.module)

    assert imported
    for name in imported:
        root = name.split(".")[0]
        assert root not in {"django", "rest_framework", "apps"}, name
