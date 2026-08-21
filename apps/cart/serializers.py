from rest_framework import serializers

from apps.products.serializers import ProductListSerializer

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    variant_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    variant_name = serializers.SerializerMethodField()
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "product_id",
            "variant",
            "variant_id",
            "variant_name",
            "quantity",
            "unit_price",
            "line_total",
        )
        read_only_fields = ("unit_price", "variant")

    def get_variant_name(self, obj):
        return obj.variant.name if obj.variant_id else ""


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "subtotal", "item_count", "updated_at")

    def get_item_count(self, obj):
        return sum(i.quantity for i in obj.items.all())


class CartItemWriteSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    variant_id = serializers.IntegerField(required=False, allow_null=True)
