from django.conf import settings
from django.core.cache import caches

LOCMEM = "django.core.cache.backends.locmem.LocMemCache"


def surviving_keys(alias, count):
    store = caches[alias]
    keys = [f"key-{number}" for number in range(count)]
    for number, key in enumerate(keys):
        store.set(key, number)
    return len(store.get_many(keys))


def test_the_cache_aliases_are_exactly_default_and_login():
    assert set(settings.CACHES) == {"default", "login"}


def test_default_is_local_memory_without_options():
    assert settings.CACHES["default"] == {"BACKEND": LOCMEM}


def test_login_has_its_own_location():
    login = settings.CACHES["login"]

    assert login["BACKEND"] == LOCMEM
    assert login["LOCATION"] == "login-attempts"
    assert login["LOCATION"] != settings.CACHES["default"].get("LOCATION", "")


def test_login_declares_its_capacity_and_cull_options():
    options = settings.CACHES["login"]["OPTIONS"]

    assert options == {"MAX_ENTRIES": 20000, "CULL_FREQUENCY": 10}


def test_login_cache_drops_a_tenth_of_its_entries_when_it_is_full():
    # Django ignora sin avisar una opción mal escrita: se mide la capacidad real
    # La 20001.ª clave expulsa 2000 y se guarda ella: 20000 - 2000 + 1
    assert surviving_keys("login", 20001) == 18001


def test_default_cache_keeps_its_capacity_of_300_entries():
    # La 301.ª clave expulsa un tercio, 100, y se guarda ella: 300 - 100 + 1
    assert surviving_keys("default", 301) == 201


def test_a_key_written_in_login_does_not_exist_in_default():
    caches["login"].set("same-name", 1)

    assert caches["default"].get("same-name") is None


def test_a_key_written_in_default_does_not_exist_in_login():
    caches["default"].set("same-name", 1)

    assert caches["login"].get("same-name") is None
