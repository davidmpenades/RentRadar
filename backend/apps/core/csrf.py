from django.http import QueryDict
from rest_framework.authentication import CSRFCheck
from rest_framework.permissions import SAFE_METHODS

from apps.core.api import ApiError


def enforce_csrf(http_request):
    # Con el POST vacío, la comprobación no lee ni analiza el cuerpo
    http_request.POST = QueryDict()
    check = CSRFCheck(lambda request: None)
    check.process_request(http_request)
    reason = check.process_view(http_request, None, (), {})
    # Se lanza fuera de cualquier except y sin el motivo, que describe lo recibido
    if reason:
        raise ApiError("csrf_failed")


class CsrfEnforcedMixin:
    # DRF solo exige el token a quien ya está autenticado; aquí también al anónimo
    def initial(self, request, *args, **kwargs):
        # Primero negociación, autenticación, permisos y límites: un 429 gana al 403
        super().initial(request, *args, **kwargs)
        method = request.method.lower()
        if (
            request.method not in SAFE_METHODS
            and method in self.http_method_names
            and hasattr(self, method)
        ):
            enforce_csrf(request._request)
