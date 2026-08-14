from django.db import models

from apps.orders.models import Order
from common.constants import (
    GATEWAY_CHAPA,
    GATEWAY_MOCK,
    GATEWAY_STRIPE,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PENDING,
    PAYMENT_STATUS_REFUNDED,
    PAYMENT_STATUS_SUCCESS,
)
from common.utils import generate_payment_reference


class Payment(models.Model):
    GATEWAYS = [
        (GATEWAY_MOCK, "Mock"),
        (GATEWAY_STRIPE, "Stripe"),
        (GATEWAY_CHAPA, "Chapa"),
    ]
    STATUS = [
        (PAYMENT_STATUS_PENDING, "Pending"),
        (PAYMENT_STATUS_SUCCESS, "Success"),
        (PAYMENT_STATUS_FAILED, "Failed"),
        (PAYMENT_STATUS_REFUNDED, "Refunded"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    reference = models.CharField(
        max_length=64, unique=True, default=generate_payment_reference
    )
    gateway = models.CharField(max_length=20, choices=GATEWAYS, default=GATEWAY_MOCK)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20, choices=STATUS, default=PAYMENT_STATUS_PENDING
    )
    gateway_payment_id = models.CharField(max_length=255, blank=True)
    checkout_url = models.URLField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} ({self.status})"


class WebhookEvent(models.Model):
    """Idempotent store for gateway webhook deliveries."""

    provider = models.CharField(max_length=20)
    event_id = models.CharField(max_length=255, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider}:{self.event_id}"
