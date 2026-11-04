from django.conf import settings
from django.contrib.auth import login
from django.core.exceptions import NON_FIELD_ERRORS
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.cache import patch_cache_control, patch_vary_headers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import ApiError
from apps.core.csrf import CsrfEnforcedMixin
from apps.core.errors import DomainValidationError
from apps.core.request_body import read_json_object, read_text_fields
from apps.core.serializers import ApiErrorSerializer
from apps.users.serializers import (
    RegistrationErrorSerializer,
    RegistrationRequestSerializer,
    SessionSerializer,
)
from apps.users.services import register_user
from apps.users.throttling import RegistrationThrottle

REGISTRATION_MAX_BYTES = 4096

# (clave del error de dominio, clave pública), en el orden en que se responden
PUBLIC_FIELDS = (
    ("email", "email"),
    ("password", "password"),
    (NON_FIELD_ERRORS, "non_field"),
)

CSRF_HEADER = OpenApiParameter(
    "X-CSRFToken",
    OpenApiTypes.STR,
    OpenApiParameter.HEADER,
    required=True,
    description="Igual al valor de la cookie csrftoken.",
)


def set_cookie_header(status_code, description):
    return OpenApiParameter(
        "Set-Cookie",
        OpenApiTypes.STR,
        OpenApiParameter.HEADER,
        response=[status_code],
        description=description,
    )


REGISTRATION_COOKIES = set_cookie_header(
    201, "Cookies sessionid (HttpOnly) y csrftoken nuevas."
)
SESSION_COOKIES = set_cookie_header(
    200, "Cookie csrftoken; borra sessionid si la sesión no es válida."
)
LOGOUT_COOKIES = set_cookie_header(204, "Borra la cookie sessionid.")


def public_field_errors(message_dict):
    return {
        public: list(message_dict[field])
        for field, public in PUBLIC_FIELDS
        if field in message_dict
    }


def _register_and_open_session(http_request, *, email, password):
    # La cuenta y su sesión nueva se crean juntas o no se crea ninguna
    try:
        with transaction.atomic():
            user = register_user(email=email, password=password)
            # Sin flush(), login() conservaría la clave o los datos de la anterior
            http_request.session.flush()
            login(http_request, user)
    except DomainValidationError as exc:
        return None, exc.message_dict
    return user, None


class RegisterView(CsrfEnforcedMixin, APIView):
    # Sin autenticación: el registro sustituye la sesión, nunca la lee
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationThrottle]
    http_method_names = ["post"]

    @extend_schema(
        operation_id="registerAccount",
        tags=["auth"],
        parameters=[CSRF_HEADER, REGISTRATION_COOKIES],
        request=RegistrationRequestSerializer,
        responses={
            201: SessionSerializer,
            400: RegistrationErrorSerializer,
            403: ApiErrorSerializer,
            405: ApiErrorSerializer,
            413: ApiErrorSerializer,
            429: ApiErrorSerializer,
        },
    )
    def post(self, request):
        http_request = request._request
        data = read_json_object(http_request, max_bytes=REGISTRATION_MAX_BYTES)
        fields = read_text_fields(data, ("email", "password"))
        user, errors = _register_and_open_session(http_request, **fields)
        # Se lanza fuera del except: el error de dominio no queda como contexto
        if errors:
            raise ApiError("invalid_fields", public_field_errors(errors))

        response = Response(
            SessionSerializer({"user": user}).data, status=status.HTTP_201_CREATED
        )
        patch_cache_control(response, no_store=True)
        return response


class CurrentSessionView(APIView):
    # Solo métodos seguros: la sesión se lee sin exigir el token CSRF
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    http_method_names = ["get", "head"]

    def initial(self, request, *args, **kwargs):
        # Antes de autenticar: con sesión, SessionAuthentication exigiría CSRF (403)
        if request.method.lower() not in self.http_method_names:
            raise MethodNotAllowed(request.method)
        super().initial(request, *args, **kwargs)

    @extend_schema(
        operation_id="getCurrentSession",
        tags=["auth"],
        parameters=[SESSION_COOKIES],
        responses={200: SessionSerializer, 405: ApiErrorSerializer},
    )
    def get(self, request):
        # El cliente recibe aquí el token que enviará en el registro y la salida
        get_token(request._request)
        user = request.user if request.user.is_authenticated else None
        response = Response(SessionSerializer({"user": user}).data)
        patch_cache_control(response, no_store=True)
        patch_vary_headers(response, ("Cookie",))
        return response


class LogoutView(CsrfEnforcedMixin, APIView):
    # Sin autenticación: se cierra la sesión de la cookie sin cargar su usuario
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["post"]

    @extend_schema(
        operation_id="logout",
        tags=["auth"],
        parameters=[CSRF_HEADER, LOGOUT_COOKIES],
        request=None,
        responses={204: None, 403: ApiErrorSerializer, 405: ApiErrorSerializer},
    )
    def post(self, request):
        # Sin cargar la sesión, flush() borra la fila por su clave aunque haya caducado
        request._request.session.flush()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        # SessionMiddleware solo la retira si viajó en la petición: aquí, siempre
        response.delete_cookie(
            settings.SESSION_COOKIE_NAME,
            path=settings.SESSION_COOKIE_PATH,
            domain=settings.SESSION_COOKIE_DOMAIN,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        patch_cache_control(response, no_store=True)
        return response
