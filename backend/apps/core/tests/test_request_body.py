import io
import json
from unittest import mock

import pytest
from django.conf import settings as django_settings
from django.core.handlers.wsgi import LimitedStream
from django.http import HttpRequest
from django.test import RequestFactory

from apps.core.api import ApiError
from apps.core.request_body import read_json_object, read_text_fields

MAX_BYTES = 4096
JSON = "application/json"
MARK = "mark-that-must-not-travel"


def make_request(body=b"{}", content_type=JSON, **meta):
    if isinstance(body, str):
        body = body.encode()
    # Sin cuerpo, RequestFactory no pone el tipo
    meta.setdefault("CONTENT_TYPE", content_type)
    return RequestFactory().generic("POST", "/x/", body, content_type, **meta)


def read(request):
    return read_json_object(request, max_bytes=MAX_BYTES)


def rejection(request):
    with pytest.raises(ApiError) as excinfo:
        read(request)
    return excinfo.value


def object_of_size(size):
    prefix, suffix = b'{"password": "', b'"}'
    body = prefix + b"x" * (size - len(prefix) - len(suffix)) + suffix
    assert len(body) == size
    return body


@pytest.fixture
def never_read():
    with mock.patch.object(LimitedStream, "read", side_effect=AssertionError):
        yield


def test_an_object_of_exactly_the_limit_passes():
    result = read(make_request(object_of_size(MAX_BYTES)))

    assert len(result["password"]) == MAX_BYTES - len('{"password": ""}')


def test_a_declared_length_over_the_limit_is_rejected_without_reading(never_read):
    error = rejection(make_request(object_of_size(MAX_BYTES + 1)))

    assert error.error_code == "payload_too_large"


def test_more_bytes_than_the_limit_are_rejected_even_if_fewer_were_declared():
    request = make_request(b"{}")
    request._stream = io.BytesIO(b"x" * (MAX_BYTES + 904))

    assert rejection(request).error_code == "payload_too_large"


def test_exactly_one_byte_over_the_limit_is_read_as_too_large():
    request = make_request(b"{}")
    request._stream = io.BytesIO(object_of_size(MAX_BYTES) + b" ")

    assert rejection(request).error_code == "payload_too_large"


@pytest.mark.parametrize("value", ["chunked", "identity", "gzip, chunked", ""])
def test_a_transfer_encoding_header_is_too_large_whatever_it_says(value):
    request = make_request(b"{}", HTTP_TRANSFER_ENCODING=value)

    assert rejection(request).error_code == "payload_too_large"


@pytest.mark.parametrize("content_type", ["text/plain", ""])
def test_a_transfer_encoding_header_wins_over_a_wrong_content_type(content_type):
    request = make_request(b"{}", content_type, HTTP_TRANSFER_ENCODING="chunked")

    assert rejection(request).error_code == "payload_too_large"


def test_a_transfer_encoding_header_is_rejected_without_reading(never_read):
    request = make_request(b"{}", HTTP_TRANSFER_ENCODING="chunked")

    assert rejection(request).error_code == "payload_too_large"


@pytest.mark.parametrize("content_type", ["text/plain", ""])
def test_a_huge_declared_length_wins_over_a_wrong_content_type(
    never_read, content_type
):
    request = make_request(b"{}", content_type, CONTENT_LENGTH="9" * 20)

    assert rejection(request).error_code == "payload_too_large"


@pytest.mark.parametrize("length", ["not-a-number", "", "-5"])
def test_an_unusable_content_length_is_an_empty_body(length):
    request = make_request(b'{"email": "ana@correo.es"}', CONTENT_LENGTH=length)

    assert read(request) == {}


@pytest.mark.parametrize(
    "content_type",
    [
        "",
        "text/plain",
        "multipart/form-data; boundary=x",
        "application/x-www-form-urlencoded",
        "application/jsonx",
    ],
)
def test_a_content_type_other_than_json_is_an_invalid_request(content_type):
    request = make_request(b"{}", content_type, CONTENT_TYPE=content_type)

    assert rejection(request).error_code == "invalid_request"


def test_the_content_type_is_matched_without_case_nor_parameters():
    request = make_request(b'{"a": 1}', "Application/JSON; charset=latin-1")

    assert read(request) == {"a": 1}


INVALID_BODIES = {
    "truncated": b'{"email": ',
    "bom": b"\xef\xbb\xbf{}",
    "nan": b'{"a": NaN}',
    "infinity": b'{"a": Infinity}',
    "invalid-utf8": b'{"a": "\xff"}',
    "trailing-garbage": b"{} x",
    "only-spaces": b"   ",
    "bare-word": b"hello",
}


@pytest.mark.parametrize("body", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
def test_a_body_that_is_not_valid_json_is_an_invalid_request(body):
    assert rejection(make_request(body)).error_code == "invalid_request"


ROOTS = {
    "list": b"[]",
    "text": b'"text"',
    "number": b"5",
    "null": b"null",
    "boolean": b"true",
    "nested-lists": b"[" * 2048 + b"]" * 2048,
}


@pytest.mark.parametrize("body", ROOTS.values(), ids=ROOTS.keys())
def test_a_root_that_is_not_an_object_is_an_invalid_request(body):
    assert rejection(make_request(body)).error_code == "invalid_request"


def test_an_object_nested_in_an_unknown_key_is_accepted():
    body = b'{"x":' * 600 + b"{}" + b"}" * 600
    assert len(body) < MAX_BYTES

    result = read(make_request(body))

    assert isinstance(result, dict)
    assert list(result) == ["x"]


def test_a_parser_that_runs_out_of_recursion_is_an_invalid_request():
    with mock.patch("apps.core.request_body.JSONParser") as parser:
        parser.return_value.parse.side_effect = RecursionError
        error = rejection(make_request(b"{}"))

    assert error.error_code == "invalid_request"


def test_an_empty_body_with_the_json_type_is_an_empty_object():
    assert read(make_request(b"")) == {}


def test_a_repeated_key_keeps_the_last_value():
    assert read(make_request(b'{"a": "first", "a": "last"}')) == {"a": "last"}


FAILING = {
    "invalid-json": (b'{"email": ' + MARK.encode(), {}),
    "root-list": (b'["' + MARK.encode() + b'"]', {}),
    "too-large-declared": (
        b'{"email": "' + MARK.encode() + b'"}',
        {"CONTENT_LENGTH": "5000"},
    ),
    "chunked": (
        b'{"email": "' + MARK.encode() + b'"}',
        {"HTTP_TRANSFER_ENCODING": "chunked"},
    ),
}


@pytest.mark.parametrize("case", FAILING.values(), ids=FAILING.keys())
def test_no_rejection_carries_a_context_nor_the_received_text(case):
    body, meta = case

    error = rejection(make_request(body, **meta))

    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.params == {}
    assert MARK not in repr(error) + str(error.detail)


def test_the_recursion_rejection_carries_no_context():
    with mock.patch("apps.core.request_body.JSONParser") as parser:
        parser.return_value.parse.side_effect = RecursionError(MARK)
        error = rejection(make_request(b"{}"))

    assert error.__context__ is None
    assert error.__cause__ is None
    assert MARK not in repr(error) + str(error.detail)


def test_the_reader_never_uses_the_body_property():
    with mock.patch.object(HttpRequest, "body", new_callable=mock.PropertyMock) as body:
        body.side_effect = AssertionError
        result = read(make_request(b'{"a": 1}'))

    assert result == {"a": 1}


def test_text_fields_absent_or_null_are_none():
    result = read_text_fields({"email": None}, ("email", "password"))

    assert result == {"email": None, "password": None}


def test_text_fields_keep_text_and_the_empty_string():
    result = read_text_fields({"email": "", "password": " x "}, ("email", "password"))

    assert result == {"email": "", "password": " x "}


@pytest.mark.parametrize(
    "value",
    [5, 1.5, True, False, ["a"], {"a": "b"}, []],
    ids=["int", "float", "true", "false", "list", "object", "empty-list"],
)
def test_text_fields_of_another_type_are_an_invalid_request(value):
    with pytest.raises(ApiError) as excinfo:
        read_text_fields({"email": "a", "password": value}, ("email", "password"))

    assert excinfo.value.error_code == "invalid_request"
    assert excinfo.value.__context__ is None


def test_text_fields_leave_out_the_ones_not_asked_for():
    data = {"email": "a", "is_staff": True, "x": {"y": 1}}

    assert read_text_fields(data, ("email",)) == {"email": "a"}


def test_the_whole_path_over_a_view(csrf_client, settings):
    settings.ROOT_URLCONF = "apps.core.tests.csrf_urls"
    token = "a1B2c3D4" * 4
    csrf_client.cookies[django_settings.CSRF_COOKIE_NAME] = token
    headers = {"X-CSRFToken": token}

    def post(body, **extra):
        return csrf_client.post(
            "/post-only/", data=body, content_type=JSON, headers=headers, **extra
        )

    ok = post(json.dumps({"email": "ana@correo.es", "password": "x", "is_staff": True}))
    assert ok.status_code == 200
    assert ok.json() == {"email": "ana@correo.es", "password": "x"}

    assert post("{}").json() == {"email": None, "password": None}
    assert post('{"email": 5}').json() == {"code": "invalid_request"}
    assert post("[]").status_code == 400
    too_large = post(object_of_size(MAX_BYTES + 1))
    assert too_large.status_code == 413
    assert too_large.json() == {"code": "payload_too_large"}
    assert too_large["Cache-Control"] == "no-store"
    chunked = post("{}", HTTP_TRANSFER_ENCODING="chunked")
    assert chunked.status_code == 413
