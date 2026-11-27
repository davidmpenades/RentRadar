import ast
from decimal import Decimal
from pathlib import Path

import pytest
from django.http import QueryDict

from apps.assets import filters
from apps.assets.filters import (
    NO_FILTERS,
    Filters,
    PublicQuery,
    parse_filters,
    parse_public_query,
)
from apps.assets.zone import Zone, ZoneError
from apps.categories.models import SLUG_PATTERN

NO_BREAK_SPACE = chr(0xA0)
IDEOGRAPHIC_SPACE = chr(0x3000)
ZERO_WIDTH_SPACE = chr(0x200B)
COMBINING_ACUTE = chr(0x301)
DELETE = chr(0x7F)
C1_CONTROL = chr(0x9F)
ARABIC_INDIC_ONE = chr(0x661)

FILTER_CODES = {"repeated", "empty", "too_long", "invalid_format", "control_char"}
VALENCIA = {"south": "39.4", "west": "-0.4", "north": "39.5", "east": "-0.3"}
VALENCIA_ZONE = Zone(
    south=Decimal("39.4"),
    west=Decimal("-0.4"),
    north=Decimal("39.5"),
    east=Decimal("-0.3"),
)


def make_params(**overrides):
    values = {**VALENCIA, **overrides}
    return {
        name: value if isinstance(value, list) else [value]
        for name, value in values.items()
    }


def assert_error(result, code, params):
    assert isinstance(result, ZoneError)
    assert result.code == code
    # El orden de las claves forma parte del contrato del error
    assert list(result.params.items()) == params


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="no-parameters"),
        pytest.param({"Category": ["-BAD"], "Q": [""]}, id="names-are-case-sensitive"),
    ],
)
def test_no_filter_parameters_return_no_filters(params):
    assert parse_filters(params) == NO_FILTERS
    assert Filters(category_slug=None, title_fragment=None) == NO_FILTERS


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param({"category": ["ski"]}, Filters("ski", None), id="category-ski"),
        pytest.param(
            {"category": ["sports-area"]},
            Filters("sports-area", None),
            id="category-sports-area",
        ),
        pytest.param(
            {"category": ["a" * 50]},
            Filters("a" * 50, None),
            id="category-of-50-characters",
        ),
        pytest.param({"q": ["  bici  "]}, Filters(None, "bici"), id="text-trimmed"),
        pytest.param({"q": ["ESQUÍ"]}, Filters(None, "esqui"), id="text-folded"),
        pytest.param(
            {"category": ["ski"], "q": ["Bici"]},
            Filters("ski", "bici"),
            id="category-and-text",
        ),
    ],
)
def test_valid_filters_are_returned_trimmed_and_folded(params, expected):
    assert parse_filters(params) == expected


@pytest.mark.parametrize("text", [pytest.param("Esqui" + COMBINING_ACUTE, id="accent")])
def test_a_text_in_nfd_is_normalised_before_folding(text):
    assert parse_filters({"q": [text]}) == Filters(None, "esqui")


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param(
            {"category": ["ski", "pool"]},
            {"category": "repeated"},
            id="category-two-values",
        ),
        pytest.param(
            {"q": ["bici", "bici"]}, {"q": "repeated"}, id="text-same-value-twice"
        ),
    ],
)
def test_a_repeated_parameter_is_rejected(params, expected):
    assert parse_filters(params) == expected


@pytest.mark.parametrize(
    "name", [pytest.param("category", id="category"), pytest.param("q", id="text")]
)
def test_an_empty_value_is_an_error_and_not_a_missing_filter(name):
    assert parse_filters({name: [""]}) == {name: "empty"}


@pytest.mark.parametrize("name", [pytest.param("q", id="q")])
def test_a_parameter_without_equals_arrives_as_an_empty_value(name):
    params = dict(QueryDict(f"south=1&{name}").lists())

    assert params[name] == [""]
    assert parse_filters(params) == {name: "empty"}


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("\t\n", id="tab-and-newline"),
        pytest.param(
            NO_BREAK_SPACE + IDEOGRAPHIC_SPACE, id="no-break-and-ideographic-space"
        ),
        pytest.param(" " * 100, id="100-spaces"),
    ],
)
def test_a_text_that_is_empty_after_trimming_is_empty(text):
    assert parse_filters({"q": [text]}) == {"q": "empty"}


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        pytest.param("a" * 64, "a" * 64, id="64"),
        pytest.param(
            NO_BREAK_SPACE + IDEOGRAPHIC_SPACE + "a" * 64 + IDEOGRAPHIC_SPACE,
            "a" * 64,
            id="64-surrounded-by-no-break-and-ideographic-spaces",
        ),
        pytest.param(
            "a" * 63 + "e" + COMBINING_ACUTE,
            "a" * 63 + "e",
            id="65-in-nfd-that-are-64-in-nfc",
        ),
    ],
)
def test_a_text_of_up_to_64_characters_is_accepted(text, fragment):
    assert parse_filters({"q": [text]}) == Filters(None, fragment)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("a" * 65, id="65"),
        pytest.param("a" * 32 + "\t" + "a" * 32, id="65-with-a-control-character"),
    ],
)
def test_a_text_of_more_than_64_characters_is_too_long(text):
    assert parse_filters({"q": [text]}) == {"q": "too_long"}


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("a\tb", id="tab"),
        pytest.param("a" + DELETE + "b", id="delete"),
        pytest.param("a" + C1_CONTROL + "b", id="c1-control"),
    ],
)
def test_a_control_character_inside_the_text_is_rejected(text):
    assert parse_filters({"q": [text]}) == {"q": "control_char"}


@pytest.mark.parametrize("text", [pytest.param("bici\n", id="line-break-at-the-end")])
def test_control_characters_at_the_ends_are_trimmed_and_not_rejected(text):
    assert parse_filters({"q": [text]}) == Filters(None, "bici")


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(ZERO_WIDTH_SPACE, id="zero-width-space"),
        pytest.param(COMBINING_ACUTE, id="combining-acute"),
    ],
)
def test_format_and_combining_characters_are_accepted_and_kept(text):
    assert parse_filters({"q": [text]}) == Filters(None, text)


@pytest.mark.parametrize(
    "slug",
    [
        pytest.param("sports--area", id="double-hyphen"),
        # Rojo si: el patrón acepta un guion al final del identificador
        pytest.param("ski-", id="trailing-hyphen"),
        pytest.param("ski\n", id="trailing-newline"),
        pytest.param("Ski", id="uppercase"),
        pytest.param(" ski", id="leading-space"),
        pytest.param("ski" + ARABIC_INDIC_ONE, id="arabic-indic-digit"),
    ],
)
def test_a_category_with_a_wrong_format_is_rejected(slug):
    assert parse_filters({"category": [slug]}) == {"category": "invalid_format"}


@pytest.mark.parametrize(
    "slug",
    [
        pytest.param("a" * 51, id="51-valid-format"),
        pytest.param("A" * 51, id="51-wrong-format"),
    ],
)
def test_a_category_of_more_than_50_characters_is_too_long(slug):
    assert parse_filters({"category": [slug]}) == {"category": "too_long"}


def test_the_category_pattern_is_the_one_of_the_category_model():
    assert filters.CATEGORY_PATTERN.pattern == SLUG_PATTERN


def test_both_filters_failing_return_both_codes_in_order():
    result = parse_filters({"q": [""], "category": ["-ski"]})

    assert list(result.items()) == [
        ("category", "invalid_format"),
        ("q", "empty"),
    ]


@pytest.mark.parametrize(
    "params",
    [pytest.param({"category": ["-ski"], "q": ["bici"]}, id="category-bad-text-ok")],
)
def test_only_the_failing_filter_is_reported(params):
    assert parse_filters(params) == {"category": "invalid_format"}


def test_every_filter_code_returned_belongs_to_the_filter_codes():
    failing = [
        {"category": ["ski", "pool"]},
        {"category": [""]},
        {"category": ["a" * 51]},
        {"category": ["-ski"]},
        {"q": ["a\tb"]},
    ]

    codes = {code for params in failing for code in parse_filters(params).values()}

    assert codes == FILTER_CODES
    assert all(type(code) is str for code in codes)


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param(
            make_params(south="abc", q=""),
            [("south", "not_a_number"), ("q", "empty")],
            id="south-and-empty-text",
        ),
        pytest.param(
            make_params(q=""), [("q", "empty")], id="valid-zone-and-empty-text"
        ),
    ],
)
def test_zone_and_filter_errors_are_returned_together(params, expected):
    assert_error(parse_public_query(params), "invalid_parameters", expected)


def test_an_inverted_zone_with_an_invalid_filter_reports_only_the_filter():
    params = make_params(south="50", north="10", q="a" * 65)

    assert_error(parse_public_query(params), "invalid_parameters", [("q", "too_long")])


@pytest.mark.parametrize(
    "params",
    [
        pytest.param(
            make_params(south="50", north="10", category="ski", q="bici"),
            id="inverted-with-valid-filters",
        )
    ],
)
def test_once_the_filters_are_valid_the_zone_error_is_reported(params):
    assert_error(parse_public_query(params), "zone_inverted", [])


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param(
            make_params(), PublicQuery(VALENCIA_ZONE, NO_FILTERS), id="without-filters"
        ),
        pytest.param(
            make_params(category="ski", q="Bici"),
            PublicQuery(VALENCIA_ZONE, Filters("ski", "bici")),
            id="with-filters",
        ),
    ],
)
def test_the_query_carries_the_zone_and_its_filters(params, expected):
    assert parse_public_query(params) == expected


def test_filters_module_stays_pure_without_django_drf_or_other_apps():
    tree = ast.parse(Path(filters.__file__).read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "sin imports relativos"
            imported.append(node.module)

    assert imported
    for name in imported:
        assert name.split(".")[0] not in {"django", "rest_framework"}, name
        if name.split(".")[0] == "apps":
            assert name in {"apps.assets.folding", "apps.assets.zone"}, name
