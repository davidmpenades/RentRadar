from django.utils.cache import patch_cache_control, patch_vary_headers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.assets.filters import parse_public_query
from apps.assets.selectors import visible_assets_in_zone
from apps.assets.serializers import PublicAssetListSerializer, PublicAssetSerializer
from apps.assets.zone import ZoneError
from apps.core.api import ApiError
from apps.core.middleware import mark_response_cookieless
from apps.core.serializers import ApiErrorSerializer

PUBLIC_LIST_LIMIT = 200
PUBLIC_LIST_MAX_AGE = 60


class PublicListThrottle(AnonRateThrottle):
    # La tasa va en la clase: THROTTLE_RATES se lee al importar y no se puede cambiar
    rate = "60/min"
    scope = "public_assets"


def _bound_parameter(name, description):
    return OpenApiParameter(
        name,
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=True,
        description=description,
    )


def _filter_parameter(name, description):
    return OpenApiParameter(
        name,
        OpenApiTypes.STR,
        OpenApiParameter.QUERY,
        required=False,
        description=description,
    )


class PublicAssetListView(APIView):
    # Sin autenticación: la respuesta es igual para todos y la sesión no se toca
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PublicListThrottle]
    http_method_names = ["get", "head"]

    @extend_schema(
        operation_id="listPublicAssets",
        tags=["public"],
        parameters=[
            _bound_parameter("south", "Latitud del límite sur de la zona."),
            _bound_parameter("west", "Longitud del límite oeste de la zona."),
            _bound_parameter("north", "Latitud del límite norte de la zona."),
            _bound_parameter("east", "Longitud del límite este de la zona."),
            _filter_parameter(
                "category",
                "Identificador de categoría (por ejemplo, ski). Limita la lista a "
                "los bienes de esa categoría. Secuencias de letras minúsculas ASCII "
                "o dígitos separadas por un guion simple, hasta 50 caracteres. Un "
                "identificador bien formado que no corresponde a ninguna categoría "
                "da una lista vacía.",
            ),
            _filter_parameter(
                "q",
                "Texto que debe contener el título, sin distinguir mayúsculas ni las "
                "tildes de las letras latinas de Europa occidental (la ñ cuenta como "
                "una letra distinta de la n). Se recorta por los extremos; hasta 64 "
                "caracteres y sin caracteres de control. Solo se compara con el "
                "título.",
            ),
        ],
        responses={
            200: PublicAssetListSerializer,
            400: ApiErrorSerializer,
            405: ApiErrorSerializer,
            429: ApiErrorSerializer,
        },
    )
    def get(self, request):
        query = parse_public_query(dict(request.query_params.lists()))
        if isinstance(query, ZoneError):
            raise ApiError(query.code, query.params)

        rows, incomplete = visible_assets_in_zone(
            zone=query.zone, limit=PUBLIC_LIST_LIMIT, filters=query.filters
        )
        response = Response(
            {
                "results": PublicAssetSerializer(rows, many=True).data,
                "incomplete": incomplete,
            }
        )
        patch_cache_control(response, public=True, max_age=PUBLIC_LIST_MAX_AGE)
        patch_vary_headers(response, ("Accept-Encoding",))
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        # También los errores: Session y CSRF les añadirían cookies que nadie necesita
        response = super().finalize_response(request, response, *args, **kwargs)
        return mark_response_cookieless(response)
