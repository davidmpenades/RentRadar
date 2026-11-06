from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from apps.core.csrf import CsrfEnforcedMixin
from apps.core.request_body import read_json_object, read_text_fields

MAX_BYTES = 4096


class Anonymous:
    authentication_classes = []
    permission_classes = [AllowAny]


class PostOnlyView(Anonymous, CsrfEnforcedMixin, APIView):
    http_method_names = ["post"]

    def post(self, request):
        data = read_json_object(request._request, max_bytes=MAX_BYTES)
        return Response(read_text_fields(data, ("email", "password")))


class PostHandlerView(Anonymous, CsrfEnforcedMixin, APIView):
    # Los métodos admitidos son los de DRF por defecto: PUT existe pero sin manejador
    def post(self, request):
        return Response({"ok": True})


class GetAndPostView(Anonymous, CsrfEnforcedMixin, APIView):
    def get(self, request):
        return Response({"ok": True})

    def post(self, request):
        return Response({"ok": True})


class AlwaysThrottled(BaseThrottle):
    def allow_request(self, request, view):
        return False

    def wait(self):
        return 3


class ThrottledView(Anonymous, CsrfEnforcedMixin, APIView):
    throttle_classes = [AlwaysThrottled]

    def post(self, request):
        return Response({"ok": True})
