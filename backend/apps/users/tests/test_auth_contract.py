import json

import pytest
from django.core.management import call_command
from rest_framework import serializers

from apps.users.serializers import (
    RegistrationErrorSerializer,
    RegistrationRequestSerializer,
    SessionSerializer,
    SessionUserSerializer,
)

REGISTER_PATH = "/api/v1/auth/register/"


@pytest.fixture
def spec(tmp_path):
    destination = tmp_path / "openapi.json"
    call_command(
        "spectacular",
        "--validate",
        "--fail-on-warn",
        "--format",
        "openapi-json",
        "--lang",
        "en",
        "--file",
        str(destination),
    )
    return json.loads(destination.read_text())


def resolve(spec, node):
    while "$ref" in node:
        target = spec
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def json_schema(content):
    return content["content"]["application/json"]["schema"]


def component_name(node):
    return node["$ref"].rsplit("/", 1)[-1]


def test_the_registration_is_a_post_with_its_operation_and_tag(spec):
    path = spec["paths"][REGISTER_PATH]

    assert set(path) == {"post"}
    assert path["post"]["operationId"] == "registerAccount"
    assert path["post"]["tags"] == ["auth"]


def test_the_registration_requires_the_csrf_header_and_nothing_else(spec):
    parameters = spec["paths"][REGISTER_PATH]["post"]["parameters"]

    assert parameters == [
        {
            "in": "header",
            "name": "X-CSRFToken",
            "schema": {"type": "string"},
            "required": True,
            "description": parameters[0]["description"],
        }
    ]


def test_the_registration_body_has_only_email_and_password(spec):
    operation = spec["paths"][REGISTER_PATH]["post"]
    body = json_schema(operation["requestBody"])

    assert component_name(body) == "RegistrationRequest"
    schema = resolve(spec, body)
    assert set(schema["properties"]) == {"email", "password"}
    assert set(schema["required"]) == {"email", "password"}


def test_the_registration_documents_each_answer_and_its_component(spec):
    responses = spec["paths"][REGISTER_PATH]["post"]["responses"]

    assert set(responses) == {"201", "400", "403", "405", "413", "429"}
    assert component_name(json_schema(responses["201"])) == "Session"
    assert component_name(json_schema(responses["400"])) == "RegistrationError"
    for status in ("403", "405", "413", "429"):
        assert component_name(json_schema(responses[status])) == "ApiError"


def test_the_success_documents_the_cookies_it_sets(spec):
    responses = spec["paths"][REGISTER_PATH]["post"]["responses"]

    assert set(responses["201"]["headers"]) == {"Set-Cookie"}
    for status in ("400", "403", "405", "413", "429"):
        assert "headers" not in responses[status]


def test_the_session_component_has_a_nullable_user_with_only_the_email(spec):
    schemas = spec["components"]["schemas"]

    session = schemas["Session"]
    assert set(session["properties"]) == {"user"}
    assert session["required"] == ["user"]
    user = session["properties"]["user"]
    assert user["nullable"] is True
    assert [component_name(ref) for ref in user["allOf"]] == ["SessionUser"]
    assert set(schemas["SessionUser"]["properties"]) == {"email"}
    assert schemas["SessionUser"]["required"] == ["email"]


def test_the_registration_error_has_optional_params_of_code_lists(spec):
    error = spec["components"]["schemas"]["RegistrationError"]

    assert set(error["properties"]) == {"code", "params"}
    assert error["required"] == ["code"]
    params = error["properties"]["params"]
    assert params["type"] == "object"
    assert params["additionalProperties"] == {
        "type": "array",
        "items": {"type": "string"},
    }


@pytest.mark.parametrize(
    ("serializer", "fields"),
    [
        (SessionUserSerializer, {"email"}),
        (SessionSerializer, {"user"}),
        (RegistrationRequestSerializer, {"email", "password"}),
        (RegistrationErrorSerializer, {"code", "params"}),
    ],
)
def test_serializers_are_explicit_white_lists(serializer, fields):
    assert not issubclass(serializer, serializers.ModelSerializer)
    assert set(serializer().fields) == fields
