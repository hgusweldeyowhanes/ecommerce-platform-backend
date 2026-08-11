from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "reference",
            "order",
            "order_number",
            "gateway",
            "amount",
            "currency",
            "status",
            "checkout_url",
            "created_at",
        )
