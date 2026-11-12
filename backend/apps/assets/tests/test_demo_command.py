import ast
import logging
import math
import re
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from apps.assets import demo
from apps.assets.demo import DEMO_ASSETS, DEMO_EMAIL, INITIAL_CENTRE
from apps.assets.management.commands import create_demo_assets as command_module
from apps.assets.models import Asset
from apps.assets.selectors import visible_assets_in_zone
from apps.assets.tests.conftest import NOW, coordinate_forms
from apps.assets.zone import Zone

COMMAND = "create_demo_assets"
EARTH_RADIUS = 6371008.8
CENTRE = (39.4699, -0.3763)
CATEGORY_SLUGS = [
    "ebike",
    "caravan",
    "motorhome",
    "van",
    "pool",
    "barbecue",
    "sports-area",
    "boat",
    "kayak",
    "canoe",
    "other",
]
SKI = "ski"
# Posiciones de la demostración, contando desde 0
SKI_POSITION = 23
SECOND_OF_THE_PAIR_POSITION = 11
PAUSED_POSITION = 24
PRIVACY_RADII = {500, 1000, 2000}
SHARED_PAIR = ((39.4579, -0.3803), (39.4581, -0.3801))
SHARED_PAIR_RADIUS = 1000
EXACT_LIMIT = 2000
PUBLIC_LIMIT = 4000
PASSWORD_SENTINEL = "Sentinel-demo-password-q7Zk2mXv9RtB4nLw"
CREATED_MESSAGE = "Creados 25 bienes de demostración (24 activos, 1 pausado)."
EXISTING_MESSAGE = "El propietario de demostración ya existe; no se ha creado nada."
ENVIRONMENT_MESSAGE = (
    "El comando de demostración solo se ejecuta en development o test."
)
DELETED = object()
REFUSED_ENVIRONMENTS = [
    pytest.param("production", id="production"),
    pytest.param("staging", id="staging"),
    pytest.param("Development", id="capitalised-development"),
    pytest.param("TEST", id="uppercase-test"),
    pytest.param("", id="empty"),
    pytest.param(" test", id="leading-space"),
    pytest.param(None, id="none"),
    pytest.param(["test"], id="unhashable-list"),
    pytest.param(DELETED, id="attribute-deleted"),
]


class InjectedFailure(Exception):
    pass


def distance_in_metres(first, second):
    (lat1, lon1), (lat2, lon2) = (
        tuple(map(math.radians, first)),
        tuple(map(math.radians, second)),
    )
    haversine = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS * math.asin(math.sqrt(haversine))


def set_environment(settings, value):
    if value is DELETED:
        del settings.ENVIRONMENT
    else:
        settings.ENVIRONMENT = value


def imports_of(path):
    found = []
    for node in ast.walk(ast.parse(Path(path).read_text())):
        if isinstance(node, ast.Import):
            found += [(alias.name, (), 0) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = tuple(alias.name for alias in node.names)
            found.append((node.module or "", names, node.level))
    return found


def run_command(**options):
    out, err = StringIO(), StringIO()
    call_command(COMMAND, stdout=out, stderr=err, **options)
    return out.getvalue(), err.getvalue()


def demo_owner():
    return get_user_model().objects.get(email=DEMO_EMAIL)


@pytest.fixture
def fixed_inputs(monkeypatch):
    monkeypatch.setattr(
        command_module.Command, "generate_password", lambda self: PASSWORD_SENTINEL
    )
    monkeypatch.setattr(command_module.Command, "current_time", lambda self: NOW)


@pytest.fixture
def calls(monkeypatch):
    counts = {"create_user": 0, "create_asset": 0, "update_asset": 0}

    def spy(name):
        real = getattr(command_module, name)

        def wrapper(*args, **kwargs):
            counts[name] += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(command_module, name, wrapper)

    for name in counts:
        spy(name)
    return counts


# --- Datos de demostracion (sin BD) ---


def test_there_are_exactly_25_demo_assets():
    assert len(DEMO_ASSETS) == 25


def test_only_the_last_demo_asset_is_left_paused():
    assert [entry.active for entry in DEMO_ASSETS] == [True] * 24 + [False]


def test_the_first_eleven_demo_assets_cover_each_seed_category_in_order():
    assert [entry.category_slug for entry in DEMO_ASSETS[:11]] == CATEGORY_SLUGS


def test_every_demo_category_is_one_of_the_seed_or_ski():
    assert {entry.category_slug for entry in DEMO_ASSETS} == set(CATEGORY_SLUGS) | {SKI}


def test_the_ski_asset_is_the_one_that_was_the_third_van():
    entry = DEMO_ASSETS[SKI_POSITION]

    assert entry.category_slug == SKI
    assert entry.title == "Equipo de esquí de pista completo"
    assert entry.description == (
        "Esquís con fijaciones, botas y bastones en varias tallas de adulto, "
        "revisados y listos para la temporada."
    )
    assert (entry.price, entry.price_unit, entry.privacy_radius) == (
        "49.90",
        "day",
        1000,
    )
    assert (entry.latitude, entry.longitude) == (39.4605, -0.3760)
    assert entry.active


def test_only_two_vans_are_left_in_the_demo_data():
    categories = [entry.category_slug for entry in DEMO_ASSETS]

    assert [i for i, slug in enumerate(categories) if slug == "van"] == [3, 14]
    assert categories.count(SKI) == 1


def test_the_pair_member_and_the_paused_asset_keep_their_place_and_data():
    pair_member = DEMO_ASSETS[SECOND_OF_THE_PAIR_POSITION]
    paused = DEMO_ASSETS[PAUSED_POSITION]

    assert (pair_member.title, pair_member.category_slug) == (
        "Bicicleta eléctrica plegable",
        "ebike",
    )
    assert (pair_member.latitude, pair_member.longitude) == SHARED_PAIR[1]
    assert (paused.title, paused.category_slug, paused.active) == (
        "Piscina infantil con toldo",
        "pool",
        False,
    )


def test_the_demo_assets_use_exactly_the_three_privacy_radii():
    assert {entry.privacy_radius for entry in DEMO_ASSETS} == PRIVACY_RADII


def test_the_demo_assets_have_distinct_titles():
    titles = [entry.title for entry in DEMO_ASSETS]

    assert len(set(titles)) == len(titles)


def test_the_demo_pair_with_a_shared_public_location_is_in_the_data():
    pair = {
        (entry.latitude, entry.longitude)
        for entry in DEMO_ASSETS
        if entry.privacy_radius == SHARED_PAIR_RADIUS
    }

    assert set(SHARED_PAIR) <= pair


def test_the_initial_centre_is_the_one_of_the_initial_view():
    assert INITIAL_CENTRE == CENTRE


def test_every_exact_location_is_within_two_kilometres_of_the_centre():
    farthest = max(
        distance_in_metres(CENTRE, (entry.latitude, entry.longitude))
        for entry in DEMO_ASSETS
    )

    assert farthest < EXACT_LIMIT


def test_the_demo_prices_are_texts_with_two_decimals():
    for entry in DEMO_ASSETS:
        assert isinstance(entry.price, str)
        assert Decimal(entry.price).as_tuple().exponent == -2


def test_the_demo_data_module_does_not_import_django_or_the_apps():
    for module, _, level in imports_of(demo.__file__):
        assert level == 0
        assert module.split(".")[0] not in {"django", "apps"}, module


# --- Arquitectura ---


def test_the_command_imports_only_the_two_writers_from_the_asset_service():
    imported = set()
    for module, names, _ in imports_of(command_module.__file__):
        if module == "apps.assets.services":
            imported |= set(names)

    assert imported == {"create_asset", "update_asset"}


@pytest.mark.parametrize("path", [command_module.__file__, demo.__file__])
def test_neither_the_command_nor_its_data_reach_the_asset_model_or_the_location(path):
    for module, names, level in imports_of(path):
        assert level == 0
        assert module not in {"apps.assets.models", "apps.assets.location"}
        assert "Asset" not in names
        if module == "apps.assets":
            assert not {"models", "location", "services"} & set(names)
        if module.startswith("apps.assets.") and not names:
            pytest.fail(f"import de módulo completo: {module}")


# --- RF-7: sin base de datos ---


@pytest.mark.parametrize("environment", REFUSED_ENVIRONMENTS)
def test_the_command_refuses_other_environments_before_touching_anything(
    settings, monkeypatch, environment
):
    set_environment(settings, environment)
    touched = []

    def forbidden(name):
        def fail(*args, **kwargs):
            touched.append(name)
            raise AssertionError(name)

        return fail

    for name in ("create_user", "create_asset", "update_asset"):
        monkeypatch.setattr(command_module, name, forbidden(name))
    for name in ("generate_password", "current_time"):
        monkeypatch.setattr(command_module.Command, name, forbidden(name))
    out, err = StringIO(), StringIO()

    with pytest.raises(CommandError) as raised:
        call_command(COMMAND, stdout=out, stderr=err)

    assert str(raised.value) == ENVIRONMENT_MESSAGE
    assert out.getvalue() == ""
    assert err.getvalue() == ""
    assert touched == []


# --- RF-6: con base de datos ---


@pytest.mark.django_db
@pytest.mark.parametrize("environment", ["development", "test"])
def test_the_command_runs_in_development_and_in_test(
    settings, fixed_inputs, environment
):
    settings.ENVIRONMENT = environment

    output, _ = run_command()

    assert output == CREATED_MESSAGE + "\n"


@pytest.mark.django_db
def test_the_first_run_creates_the_owner_with_a_usable_random_password(fixed_inputs):
    run_command()

    owner = demo_owner()
    assert owner.email.endswith("@example.com")
    assert owner.is_active
    assert owner.check_password(PASSWORD_SENTINEL)


@pytest.mark.django_db
def test_the_first_run_creates_25_assets_24_active_and_the_last_one_paused(
    fixed_inputs,
):
    run_command()

    assets = list(Asset.objects.filter(owner=demo_owner()).order_by("-created_at"))
    assert len(assets) == 25
    assert [asset.status for asset in assets] == ["active"] * 24 + ["paused"]
    assert assets[-1].title == DEMO_ASSETS[-1].title


@pytest.mark.django_db
def test_the_demo_assets_cover_every_category_and_the_three_radii(fixed_inputs):
    run_command()

    assets = Asset.objects.filter(owner=demo_owner()).select_related("category")
    assert {asset.category.slug for asset in assets} == set(CATEGORY_SLUGS) | {SKI}
    assert {asset.privacy_radius for asset in assets} == PRIVACY_RADII


@pytest.mark.django_db
def test_the_command_creates_one_active_ski_asset(fixed_inputs):
    run_command()

    ski_asset = Asset.objects.get(owner=demo_owner(), category__slug=SKI)
    assert ski_asset.title == DEMO_ASSETS[SKI_POSITION].title
    assert ski_asset.status == "active"


@pytest.mark.django_db
def test_every_stored_public_location_is_within_four_kilometres_of_the_centre(
    fixed_inputs,
):
    run_command()

    distances = [
        distance_in_metres(CENTRE, (asset.public_location.y, asset.public_location.x))
        for asset in Asset.objects.filter(owner=demo_owner())
    ]
    assert len(distances) == 25
    assert max(distances) < PUBLIC_LIMIT


@pytest.mark.django_db
def test_exactly_the_expected_pair_shares_public_location_and_radius(fixed_inputs):
    run_command()

    groups = {}
    for asset in Asset.objects.filter(owner=demo_owner()):
        key = (asset.public_location.coords, asset.privacy_radius)
        groups.setdefault(key, set()).add(asset.title)
    shared = [titles for titles in groups.values() if len(titles) >= 2]
    expected = {
        entry.title
        for entry in DEMO_ASSETS
        if (entry.latitude, entry.longitude) in SHARED_PAIR
    }
    assert len(expected) == 2
    assert shared == [expected]


@pytest.mark.django_db
def test_each_asset_is_created_one_more_minute_in_the_past(fixed_inputs):
    run_command()

    created = {
        asset.title: asset.created_at
        for asset in Asset.objects.filter(owner=demo_owner())
    }
    assert created == {
        entry.title: NOW - timedelta(minutes=index)
        for index, entry in enumerate(DEMO_ASSETS)
    }


@pytest.mark.django_db
def test_the_assets_are_written_through_the_service_25_and_24_times(
    fixed_inputs, calls
):
    run_command()

    assert calls == {"create_user": 1, "create_asset": 25, "update_asset": 24}


@pytest.mark.django_db
def test_the_public_selector_returns_the_24_active_assets_and_not_the_paused_one(
    fixed_inputs,
):
    run_command()

    zone = Zone(
        south=Decimal("39.42"),
        west=Decimal("-0.44"),
        north=Decimal("39.52"),
        east=Decimal("-0.31"),
    )
    rows, incomplete = visible_assets_in_zone(zone=zone, limit=200)

    assert len(rows) == 24
    assert incomplete is False
    assert DEMO_ASSETS[-1].title not in {row["title"] for row in rows}


@pytest.mark.django_db
def test_the_second_run_creates_nothing_and_says_so(fixed_inputs, calls):
    run_command()
    users, assets = get_user_model().objects.count(), Asset.objects.count()
    for name in calls:
        calls[name] = 0

    output, error = run_command()

    assert output == EXISTING_MESSAGE + "\n"
    assert error == ""
    assert get_user_model().objects.count() == users
    assert Asset.objects.count() == assets
    assert calls == {"create_user": 0, "create_asset": 0, "update_asset": 0}
    assert PASSWORD_SENTINEL.lower() not in output.lower()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("writer", "failing_call"), [("update_asset", 10), ("create_asset", 7)]
)
def test_a_failure_halfway_leaves_neither_the_owner_nor_any_asset(
    fixed_inputs, monkeypatch, writer, failing_call
):
    real = getattr(command_module, writer)
    seen = 0

    def failing(*args, **kwargs):
        nonlocal seen
        seen += 1
        if seen == failing_call:
            raise InjectedFailure
        return real(*args, **kwargs)

    monkeypatch.setattr(command_module, writer, failing)
    users = get_user_model().objects.count()
    assets = Asset.objects.count()

    with pytest.raises(InjectedFailure):
        run_command()

    assert not get_user_model().objects.filter(email=DEMO_EMAIL).exists()
    assert get_user_model().objects.count() == users
    assert Asset.objects.count() == assets


# --- Logs y salida ---


@pytest.mark.django_db
def test_neither_the_output_nor_the_logs_contain_exact_coordinates_or_the_password(
    caplog, fixed_inputs
):
    caplog.set_level(logging.DEBUG)
    backends = logging.getLogger("django.db.backends")
    assert backends.getEffectiveLevel() >= logging.INFO, (
        "django.db.backends está por debajo de INFO: este test daría un falso verde"
    )
    assert connection.force_debug_cursor is False, (
        "force_debug_cursor está activo: este test daría un falso verde"
    )
    backends.info("control-positivo-de-captura")
    assert "control-positivo-de-captura" in caplog.text

    output, error = run_command()
    second_output, second_error = run_command()

    forbidden = [PASSWORD_SENTINEL] + [
        form
        for entry in DEMO_ASSETS
        for form in coordinate_forms(entry.longitude, entry.latitude)
    ]
    for text in (output, error, caplog.text):
        lowered = text.lower()
        for form in forbidden:
            assert form.lower() not in lowered, form
    for text in (second_output, second_error):
        assert PASSWORD_SENTINEL.lower() not in text.lower()


def test_the_real_password_generator_is_long_url_safe_and_different_each_time():
    command = command_module.Command()

    first, second = command.generate_password(), command.generate_password()

    assert first != second
    assert len(first) >= 43
    assert re.fullmatch(r"[A-Za-z0-9_-]+", first)


def test_the_real_clock_gives_an_aware_utc_moment():
    moment = command_module.Command().current_time()

    assert moment.utcoffset() == timedelta(0)
