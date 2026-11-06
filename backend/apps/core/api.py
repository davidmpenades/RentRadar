from collections.abc import Mapping

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

ERROR_CODES = frozenset(
    {
        "invalid_parameters",
        "zone_inverted",
        "zone_too_large",
        "method_not_allowed",
        "throttled",
        "not_found",
        "forbidden",
        "bad_request",
        "invalid_fields",
        "invalid_request",
        "payload_too_large",
        "csrf_failed",
    }
)

# Los códigos que no son un 400 corriente
STATUS_BY_CODE = {
    "csrf_failed": status.HTTP_403_FORBIDDEN,
    "payload_too_large": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
}


class ApiError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, code: str, params: Mapping[str, str | list[str]] | None = None):
        if code not in ERROR_CODES:
            raise ValueError(f"Código de error desconocido: {code}")
        super().__init__(detail=code, code=code)
        self.error_code = code
        self.status_code = STATUS_BY_CODE.get(code, status.HTTP_400_BAD_REQUEST)
        # Las listas se copian: quien llama podría seguir cambiándolas
        self.params = {
            name: list(value) if isinstance(value, list) else value
            for name, value in (params or {}).items()
        }


def _general_code(status_code: int) -> str:
    if status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    if status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return "method_not_allowed"
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "throttled"
    if status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        return "forbidden"
    return "bad_request"


def api_exception_handler(exc, context):
    # El cuerpo se construye a mano: el detalle de DRF puede repetir valores recibidos
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    if not isinstance(exc, exceptions.APIException) or exc.status_code >= 500:
        return None

    headers = {"Cache-Control": "no-store"}
    if isinstance(exc, ApiError):
        body = {"code": exc.error_code}
        if exc.params:
            body["params"] = exc.params
    else:
        body = {"code": _general_code(exc.status_code)}
    if isinstance(exc, exceptions.Throttled):
        retry_after = max(1, exc.wait or 1)
        body["retry_after"] = retry_after
        headers["Retry-After"] = str(retry_after)
    if getattr(exc, "auth_header", None):
        headers["WWW-Authenticate"] = exc.auth_header
    set_rollback()
    return Response(body, status=exc.status_code, headers=headers)
