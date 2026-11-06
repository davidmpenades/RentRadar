from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers


# Listas blancas explícitas: un campo nuevo del modelo no llega a la API por accidente
class SessionUserSerializer(serializers.Serializer):
    email = serializers.CharField(read_only=True)


class SessionSerializer(serializers.Serializer):
    user = SessionUserSerializer(read_only=True, allow_null=True)


# Solo describe la petición: la vista lee el cuerpo con su lector acotado.
# drf-spectacular añade «Request» al nombre: el componente queda RegistrationRequest
@extend_schema_serializer(component_name="Registration")
class RegistrationRequestSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)


class RegistrationErrorSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    # Sin read_only: drf-spectacular publica como obligatorio todo campo de solo lectura
    params = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()), required=False
    )
