import logging
import traceback
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.db import connection, transaction
from django.db.models import ProtectedError

from apps.assets.location import ApproximationError, approximate_location
from apps.assets.models import Asset
from apps.assets.services import create_asset, update_asset
from apps.assets.tests.conftest import (
    NOW,
    SENTINEL_LATITUDE,
    SENTINEL_LONGITUDE,
    coordinate_forms,
)
from apps.core.errors import DomainValidationError

MOVED_LATITUDE = 40.5123456
MOVED_LONGITUDE = -3.6123456
INVALID_LATITUDE = 91.4168456
# Fuera del dominio de la proyección: la aproximación falla con un error de GDAL
ANTIPODE_LATITUDE = -52.0000001
ANTIPODE_LONGITUDE = -170.0
RADIUS = 1000
LOGGERS = ("django.contrib.gis", "psycopg")


def forms_of(latitude, longitude, *, projected=True):
    return coordinate_forms(longitude, latitude, projected=projected)


def forms_with_derived_public(latitude, longitude):
    public_latitude, public_longitude = approximate_location(
        latitude, longitude, RADIUS
    )
    return forms_of(latitude, longitude) + forms_of(public_latitude, public_longitude)


EXACT_AND_PUBLIC = forms_with_derived_public(SENTINEL_LATITUDE, SENTINEL_LONGITUDE)
MOVED_AND_ITS_PUBLIC = forms_with_derived_public(MOVED_LATITUDE, MOVED_LONGITUDE)
# Con las coordenadas intercambiadas, la longitud ocupa el lugar de la latitud
SWAPPED = forms_of(SENTINEL_LONGITUDE, SENTINEL_LATITUDE, projected=False)


def watch_logs(monkeypatch, caplog):
    # Todo lo que pueda escribirse, escrito: el cursor de depuración registra cada SQL
    caplog.set_level(logging.DEBUG)
    for logger in LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger)
    monkeypatch.setattr(connection, "force_debug_cursor", True)
    caplog.clear()


def assert_no_leak(error, caplog, forms):
    texts = [
        str(error),
        repr(error),
        "".join(traceback.format_exception(error)),
        caplog.text,
    ]
    if isinstance(error, DomainValidationError):
        texts.append(str(error.message_dict))
    if isinstance(error, (DomainValidationError, ApproximationError)):
        assert error.__context__ is None
        assert error.__cause__ is None
    for text in texts:
        for form in forms:
            assert form.lower() not in text.lower()


SENTINEL_FORMS = coordinate_forms(SENTINEL_LONGITUDE, SENTINEL_LATITUDE)


def error_with_the_form_in_its_message(form, monkeypatch, caplog):
    return ValueError(f"fallo con {form}")


def error_with_the_form_in_the_log(form, monkeypatch, caplog):
    watch_logs(monkeypatch, caplog)
    logging.getLogger("django.contrib.gis").error(form)
    return ValueError("fallo sin coordenadas")


FORM_SINKS = {
    "message": error_with_the_form_in_its_message,
    "log": error_with_the_form_in_the_log,
}


@pytest.fixture
def sentinel_arguments(creation_arguments):
    return {
        **creation_arguments,
        "latitude": SENTINEL_LATITUDE,
        "longitude": SENTINEL_LONGITUDE,
    }


@pytest.fixture
def sentinel_asset(sentinel_arguments):
    return create_asset(**sentinel_arguments)


CREATION_REJECTIONS = {
    "validation": ({"title": "ab"}, EXACT_AND_PUBLIC),
    "swapped_coordinates": (
        {"latitude": SENTINEL_LONGITUDE, "longitude": SENTINEL_LATITUDE},
        EXACT_AND_PUBLIC + SWAPPED,
    ),
    "out_of_range_latitude": (
        {"latitude": INVALID_LATITUDE},
        EXACT_AND_PUBLIC
        + forms_of(INVALID_LATITUDE, SENTINEL_LONGITUDE, projected=False),
    ),
}


@pytest.mark.parametrize(
    ("overrides", "forms"), CREATION_REJECTIONS.values(), ids=CREATION_REJECTIONS
)
def test_a_creation_rejected_by_validation_does_not_leak(
    monkeypatch, caplog, sentinel_arguments, overrides, forms
):
    watch_logs(monkeypatch, caplog)

    with pytest.raises(DomainValidationError) as raised:
        create_asset(**{**sentinel_arguments, **overrides})

    assert_no_leak(raised.value, caplog, forms)


def test_a_check_violation_does_not_leak_and_leaves_the_connection_usable(
    monkeypatch, caplog, sentinel_arguments
):
    monkeypatch.setattr(
        "apps.assets.services.clean_price", lambda raw: (Decimal("0.00"), [])
    )
    watch_logs(monkeypatch, caplog)

    with pytest.raises(DomainValidationError) as raised:
        create_asset(**sentinel_arguments)

    assert raised.value.message_dict == {"price": ["price_out_of_range"]}
    assert_no_leak(raised.value, caplog, EXACT_AND_PUBLIC)
    assert Asset.objects.count() == 0


def test_a_failed_approximation_in_the_service_does_not_leak(
    monkeypatch, caplog, sentinel_arguments
):
    def fail(latitude, longitude, radius):
        raise ApproximationError("projection_failed")

    monkeypatch.setattr("apps.assets.services.approximate_location", fail)
    watch_logs(monkeypatch, caplog)

    with pytest.raises(DomainValidationError) as raised:
        create_asset(**sentinel_arguments)

    assert raised.value.message_dict == {"__all__": ["approximation_failed"]}
    assert_no_leak(raised.value, caplog, EXACT_AND_PUBLIC)


def test_a_location_locked_modification_does_not_leak(
    monkeypatch, caplog, sentinel_asset
):
    Asset.objects.filter(pk=sentinel_asset.pk).update(status="active")
    watch_logs(monkeypatch, caplog)

    with pytest.raises(DomainValidationError) as raised:
        update_asset(
            now=NOW,
            asset_id=sentinel_asset.pk,
            latitude=MOVED_LATITUDE,
            longitude=MOVED_LONGITUDE,
        )

    assert raised.value.message_dict == {"location": ["location_locked"]}
    assert_no_leak(raised.value, caplog, EXACT_AND_PUBLIC + MOVED_AND_ITS_PUBLIC)


def test_a_modification_rejected_by_validation_does_not_leak(
    monkeypatch, caplog, sentinel_asset
):
    watch_logs(monkeypatch, caplog)

    with pytest.raises(DomainValidationError) as raised:
        update_asset(
            now=NOW,
            asset_id=sentinel_asset.pk,
            title="ab",
            latitude=MOVED_LATITUDE,
            longitude=MOVED_LONGITUDE,
        )

    assert_no_leak(raised.value, caplog, EXACT_AND_PUBLIC + MOVED_AND_ITS_PUBLIC)


APPROXIMATION_FAILURES = {
    "radius": (SENTINEL_LATITUDE, SENTINEL_LONGITUDE, 1500, EXACT_AND_PUBLIC),
    "coordinate": (
        INVALID_LATITUDE,
        SENTINEL_LONGITUDE,
        RADIUS,
        forms_of(INVALID_LATITUDE, SENTINEL_LONGITUDE, projected=False),
    ),
    "projection": (
        ANTIPODE_LATITUDE,
        ANTIPODE_LONGITUDE,
        RADIUS,
        forms_of(ANTIPODE_LATITUDE, ANTIPODE_LONGITUDE, projected=False),
    ),
}


@pytest.mark.parametrize(
    ("latitude", "longitude", "radius", "forms"),
    APPROXIMATION_FAILURES.values(),
    ids=APPROXIMATION_FAILURES,
)
def test_a_failure_of_the_approximation_does_not_leak(
    monkeypatch, caplog, latitude, longitude, radius, forms
):
    watch_logs(monkeypatch, caplog)

    with pytest.raises(ApproximationError) as raised:
        approximate_location(latitude, longitude, radius)

    assert_no_leak(raised.value, caplog, forms)


def test_deleting_the_owner_of_an_asset_does_not_leak(
    monkeypatch, caplog, sentinel_asset, owner
):
    watch_logs(monkeypatch, caplog)

    with pytest.raises(ProtectedError) as raised:
        owner.delete()

    assert_no_leak(raised.value, caplog, EXACT_AND_PUBLIC)


def test_deleting_the_category_of_an_asset_does_not_leak(
    monkeypatch, caplog, sentinel_asset, category
):
    watch_logs(monkeypatch, caplog)

    with pytest.raises(ProtectedError) as raised:
        category.delete()

    assert_no_leak(raised.value, caplog, EXACT_AND_PUBLIC)


def test_reverting_the_seed_with_an_asset_does_not_leak(
    monkeypatch, caplog, sentinel_asset
):
    watch_logs(monkeypatch, caplog)

    with transaction.atomic():
        with pytest.raises(ProtectedError) as raised:
            call_command("migrate", "categories", "0001_initial", verbosity=0)
        transaction.set_rollback(True)

    assert_no_leak(raised.value, caplog, EXACT_AND_PUBLIC)


def test_the_text_of_an_asset_does_not_leak(sentinel_asset):
    stored = Asset.objects.get(pk=sentinel_asset.pk)

    for text in (str(stored), repr(stored)):
        for form in EXACT_AND_PUBLIC:
            assert form.lower() not in text.lower()


@pytest.mark.parametrize("sink", FORM_SINKS.values(), ids=FORM_SINKS)
@pytest.mark.parametrize(
    "form", SENTINEL_FORMS, ids=[f"form_{n}" for n in range(len(SENTINEL_FORMS))]
)
def test_the_detector_catches_every_form_in_every_place_it_looks(
    monkeypatch, caplog, form, sink
):
    error = sink(form, monkeypatch, caplog)

    with pytest.raises(AssertionError):
        assert_no_leak(error, caplog, SENTINEL_FORMS)


def test_the_detector_lets_a_clean_error_and_log_pass(monkeypatch, caplog):
    watch_logs(monkeypatch, caplog)
    logging.getLogger("django.contrib.gis").error("GDAL_ERROR 1: fixed message")

    assert_no_leak(ValueError("fallo sin coordenadas"), caplog, SENTINEL_FORMS)
