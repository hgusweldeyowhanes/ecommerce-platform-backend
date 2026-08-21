from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "product_name",
            "sku",
            "variant_name",
            "unit_price",
            "quantity",
            "line_total",
        )


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "status",
            "email",
            "currency",
            "subtotal",
            "shipping_fee",
            "tax",
            "total",
            "shipping_name",
            "shipping_line1",
            "shipping_line2",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "shipping_phone",
            "notes",
            "coupon_code",
            "discount",
            "tracking_number",
            "carrier",
            "shipped_at",
            "items",
            "created_at",
            "paid_at",
        )
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    email = serializers.EmailField()
    shipping_name = serializers.CharField(max_length=200)
    shipping_line1 = serializers.CharField(max_length=255)
    shipping_line2 = serializers.CharField(required=False, allow_blank=True)
    shipping_city = serializers.CharField(max_length=100)
    shipping_state = serializers.CharField(required=False, allow_blank=True)
    shipping_postal_code = serializers.CharField(required=False, allow_blank=True)
    shipping_country = serializers.CharField(max_length=2, default="US")
    shipping_phone = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    shipping_fee = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=0
    )
    payment_gateway = serializers.ChoiceField(
        choices=["mock", "stripe", "chapa"], required=False
    )
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)

