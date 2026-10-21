import re

import pytest
from django.conf import settings

from config.env import KNOWN_VARIABLES

TEMPLATE = settings.BASE_DIR.parent / ".env.example"
SECTION = re.compile(r"^# --- (?P<name>.+) ---$")
ASSIGNMENT = re.compile(r"^(?P<name>[A-Z][A-Z0-9_]*)=(?P<value>.*)$")
BACKEND_SECTION = "Backend"
FOREIGN_SECTION = "Ajeno al backend"
READABLE_VALUE = re.compile(r"^[A-Za-z0-9._,:-]+$")
SECRET_VARIABLES = ("DJANGO_SECRET_KEY", "DB_PASSWORD")


def parse_template():
    """Devuelve {bloque: {variable: (valor, con_descripción)}}."""
    sections = {}
    current = None
    previous_is_comment = False
    for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
        header = SECTION.match(line)
        if header:
            current = sections.setdefault(header["name"], {})
            previous_is_comment = False
            continue
        assignment = ASSIGNMENT.match(line)
        if assignment:
            assert current is not None, f"Variable fuera de un bloque: {line}"
            current[assignment["name"]] = (assignment["value"], previous_is_comment)
        previous_is_comment = line.startswith("#")
    return sections


@pytest.fixture(scope="module")
def sections():
    return parse_template()


def test_template_exists_and_has_only_the_two_blocks(sections):
    assert set(sections) == {BACKEND_SECTION, FOREIGN_SECTION}


def test_backend_block_matches_known_variables(sections):
    assert set(sections[BACKEND_SECTION]) == KNOWN_VARIABLES


def test_foreign_variables_are_not_read_by_the_backend(sections):
    foreign = set(sections[FOREIGN_SECTION])
    assert foreign
    assert foreign.isdisjoint(KNOWN_VARIABLES)


def test_every_variable_has_a_description_comment(sections):
    undescribed = [
        name
        for block in sections.values()
        for name, (_, described) in block.items()
        if not described
    ]
    assert undescribed == []


def test_secret_examples_are_marked_insecure(sections):
    backend = sections[BACKEND_SECTION]
    for name in SECRET_VARIABLES:
        assert "insecure-" in backend[name][0], name


def test_backend_examples_are_readable_and_not_empty(sections):
    for name, (value, _) in sections[BACKEND_SECTION].items():
        assert READABLE_VALUE.match(value), name


def test_backend_template_enables_debug(sections):
    assert sections[BACKEND_SECTION]["DJANGO_DEBUG"][0] == "true"
