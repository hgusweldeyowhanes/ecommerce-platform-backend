from rest_framework import serializers

from apps.products.serializers import ProductListSerializer

from .models import WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ("id", "product", "created_at")


class WishlistSerializer(serializers.Serializer):
    items = WishlistItemSerializer(many=True)
    item_count = serializers.IntegerField()


class ProductIdSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
