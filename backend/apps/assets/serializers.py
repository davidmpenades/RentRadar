from rest_framework import serializers


class PublicAssetSerializer(serializers.Serializer):
    # Lista blanca explícita: un campo nuevo del modelo no llega a la API por accidente
    public_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    category_slug = serializers.CharField(source="category__slug", read_only=True)
    category_name = serializers.CharField(source="category__name", read_only=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    price_unit = serializers.CharField(read_only=True)
    privacy_radius = serializers.IntegerField(read_only=True)
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)


# Solo describe la respuesta en la documentación de la API
class PublicAssetListSerializer(serializers.Serializer):
    results = PublicAssetSerializer(many=True, read_only=True)
    incomplete = serializers.BooleanField(read_only=True)
