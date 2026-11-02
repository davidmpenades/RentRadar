from django.utils.cache import patch_cache_control, patch_vary_headers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.assets.selectors import visible_assets_in_zone
from apps.assets.serializers import (
    ApiErrorSerializer,
    PublicAssetListSerializer,
    PublicAssetSerializer,
)
from apps.assets.zone import ZoneError, parse_zone
from apps.core.api import ApiError
from apps.core.middleware import mark_response_cookieless

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
        ],
        responses={
            200: PublicAssetListSerializer,
            400: ApiErrorSerializer,
            405: ApiErrorSerializer,
            429: ApiErrorSerializer,
        },
    )
    def get(self, request):
        zone = parse_zone(dict(request.query_params.lists()))
        if isinstance(zone, ZoneError):
            raise ApiError(zone.code, zone.params)

        rows, incomplete = visible_assets_in_zone(zone=zone, limit=PUBLIC_LIST_LIMIT)
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
