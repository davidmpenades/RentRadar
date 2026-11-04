from rest_framework import serializers


class ApiErrorSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    # Sin read_only: drf-spectacular publica como obligatorio todo campo de solo lectura
    params = serializers.DictField(child=serializers.CharField(), required=False)
    retry_after = serializers.IntegerField(min_value=1, required=False)
