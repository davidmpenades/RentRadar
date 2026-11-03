import pytest
from django.conf import settings

REST_FRAMEWORK_EXPECTED = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_CONTENT_NEGOTIATION_CLASS": "apps.core.negotiation.JSONOnlyNegotiation",
    "URL_FORMAT_OVERRIDE": None,
    "DEFAULT_VERSIONING_CLASS": None,
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": [],
    "NUM_PROXIES": 0,
    "EXCEPTION_HANDLER": "apps.core.api.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_EXPECTED = {
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "VERSION": "1.0.0",
}


def test_drf_and_spectacular_are_installed_apps():
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "drf_spectacular" in settings.INSTALLED_APPS


@pytest.mark.parametrize(("name", "expected"), REST_FRAMEWORK_EXPECTED.items())
def test_rest_framework_setting(name, expected):
    assert settings.REST_FRAMEWORK[name] == expected


def test_rest_framework_has_no_other_settings():
    assert set(settings.REST_FRAMEWORK) == set(REST_FRAMEWORK_EXPECTED)


@pytest.mark.parametrize(("name", "expected"), SPECTACULAR_EXPECTED.items())
def test_spectacular_setting(name, expected):
    assert settings.SPECTACULAR_SETTINGS[name] == expected


def test_drf_resolves_the_configured_classes():
    from rest_framework.parsers import JSONParser
    from rest_framework.renderers import JSONRenderer
    from rest_framework.settings import api_settings

    from apps.core.api import api_exception_handler
    from apps.core.negotiation import JSONOnlyNegotiation

    assert [JSONRenderer] == api_settings.DEFAULT_RENDERER_CLASSES
    assert [JSONParser] == api_settings.DEFAULT_PARSER_CLASSES
    assert api_settings.DEFAULT_CONTENT_NEGOTIATION_CLASS is JSONOnlyNegotiation
    assert api_settings.EXCEPTION_HANDLER is api_exception_handler


def test_append_slash_is_not_changed():
    assert settings.APPEND_SLASH is True
