from io import BytesIO

from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser

from apps.core.api import ApiError


def _declared_length(http_request) -> int:
    # Como Django: lo que no es un número cuenta como un cuerpo vacío
    try:
        return int(http_request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return 0


def _parse(raw: bytes) -> object | None:
    try:
        return JSONParser().parse(BytesIO(raw), "application/json", {})
    except (ParseError, RecursionError):
        return None


def read_json_object(http_request, *, max_bytes: int) -> dict:
    # Bajo WSGI un cuerpo troceado llega vacío y no se puede medir
    if "HTTP_TRANSFER_ENCODING" in http_request.META:
        raise ApiError("payload_too_large")
    if _declared_length(http_request) > max_bytes:
        raise ApiError("payload_too_large")
    if http_request.content_type != "application/json":
        raise ApiError("invalid_request")

    # Un byte de más basta para saber que se pasa, sin leer el resto
    raw = http_request.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ApiError("payload_too_large")
    if not raw:
        return {}

    # El error del analizador puede citar el texto recibido: se lanza fuera del except
    data = _parse(raw)
    if not isinstance(data, dict):
        raise ApiError("invalid_request")
    return data


def read_text_fields(data: dict, names) -> dict[str, str | None]:
    fields = {name: data.get(name) for name in names}
    if any(
        value is not None and not isinstance(value, str) for value in fields.values()
    ):
        raise ApiError("invalid_request")
    return fields
