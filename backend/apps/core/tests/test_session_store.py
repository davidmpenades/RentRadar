import re

import pytest
from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore

from apps.core.session_store import SessionStore
from apps.core.tests.helpers import KEY_WITHOUT_ROW

WELL_FORMED_KEYS = {
    "letters": "a" * 32,
    "digits": "0" * 32,
    "mixed": KEY_WITHOUT_ROW,
}

MALFORMED_KEYS = {
    "none": None,
    "empty": "",
    "seven-characters": "a" * 7,
    "31-characters": "a" * 31,
    "33-characters": "a" * 33,
    "uppercase": KEY_WITHOUT_ROW.upper(),
    "n-with-tilde": "a" * 31 + chr(0xF1),
    "arabic-indic-digit": "a" * 31 + chr(0x663),
    "eight-nulls": chr(0) * 8,
    "thirty-two-nulls": chr(0) * 32,
    "control-character": "a" * 31 + chr(0x1F),
    "trailing-newline": "a" * 32 + chr(0x0A),
    "leading-space": " " + "a" * 31,
    "trailing-space": "a" * 31 + " ",
    "hyphen": "a" * 16 + "-" + "a" * 15,
    "long-with-hyphens": "no-es-una-clave-de-sesion-" * 3,
}


@pytest.mark.parametrize("key", WELL_FORMED_KEYS.values(), ids=WELL_FORMED_KEYS.keys())
def test_a_well_formed_key_is_kept(key):
    assert SessionStore(key).session_key == key


@pytest.mark.parametrize("key", MALFORMED_KEYS.values(), ids=MALFORMED_KEYS.keys())
def test_a_malformed_key_is_no_session(key):
    assert SessionStore(key).session_key is None


def test_the_store_only_redefines_the_key_validation():
    redefined = {
        name
        for name in vars(SessionStore)
        if not (name.startswith("__") and name.endswith("__"))
    }

    assert redefined == {"_validate_session_key"}
    assert issubclass(SessionStore, DatabaseSessionStore)


@pytest.mark.django_db
def test_keys_created_by_django_are_well_formed():
    store = SessionStore()
    store.create()
    created = store.session_key
    store.cycle_key()

    for key in (created, store.session_key):
        assert re.fullmatch(r"[a-z0-9]{32}", key)
