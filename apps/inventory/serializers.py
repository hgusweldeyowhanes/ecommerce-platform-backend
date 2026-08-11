from rest_framework import serializers

from .models import InventoryItem, StockMovement


class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    available = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "product",
            "product_name",
            "sku",
            "quantity",
            "reserved",
            "available",
            "low_stock_threshold",
            "updated_at",
        )
        read_only_fields = ("product", "reserved", "updated_at")


class StockAdjustSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    delta = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True)


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ("id", "move_type", "quantity", "note", "reference", "created_at")
