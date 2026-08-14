from django.conf import settings
from django.db import models

from apps.products.models import Product
from common.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_PROCESSING,
    ORDER_STATUS_REFUNDED,
    ORDER_STATUS_SHIPPED,
)
from common.utils import generate_order_number


class Order(models.Model):
    STATUS_CHOICES = [
        (ORDER_STATUS_PENDING, "Pending"),
        (ORDER_STATUS_PAID, "Paid"),
        (ORDER_STATUS_PROCESSING, "Processing"),
        (ORDER_STATUS_SHIPPED, "Shipped"),
        (ORDER_STATUS_DELIVERED, "Delivered"),
        (ORDER_STATUS_CANCELLED, "Cancelled"),
        (ORDER_STATUS_REFUNDED, "Refunded"),
    ]

    order_number = models.CharField(max_length=32, unique=True, default=generate_order_number)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    email = models.EmailField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=ORDER_STATUS_PENDING, db_index=True
    )
    currency = models.CharField(max_length=3, default="USD")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    shipping_name = models.CharField(max_length=200)
    shipping_line1 = models.CharField(max_length=255)
    shipping_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_postal_code = models.CharField(max_length=32, blank=True)
    shipping_country = models.CharField(max_length=2, default="US")
    shipping_phone = models.CharField(max_length=32, blank=True)

    notes = models.TextField(blank=True)
    coupon_code = models.CharField(max_length=40, blank=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    idempotency_key = models.CharField(max_length=64, blank=True, db_index=True)
    tracking_number = models.CharField(max_length=80, blank=True)
    carrier = models.CharField(max_length=40, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uniq_user_checkout_idempotency",
            )
        ]

    def __str__(self):
        return self.order_number

    def recompute_totals(self):
        self.subtotal = sum(i.line_total for i in self.items.all())
        self.total = self.subtotal + self.shipping_fee + self.tax - self.discount
        if self.total < 0:
            self.total = 0
        self.save(update_fields=["subtotal", "total", "updated_at"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True
    )
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


class Coupon(models.Model):
    code = models.CharField(max_length=40, unique=True)
    percent_off = models.PositiveSmallIntegerField(default=0)
    amount_off = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    min_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.code

    def is_valid(self, subtotal=None):
        from django.utils import timezone
        from decimal import Decimal

        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses is not None and self.times_used >= self.max_uses:
            return False
        if subtotal is not None and Decimal(str(subtotal)) < self.min_subtotal:
            return False
        return True

    def compute_discount(self, subtotal):
        from decimal import Decimal

        subtotal = Decimal(str(subtotal))
        if self.percent_off:
            return (subtotal * self.percent_off / 100).quantize(Decimal("0.01"))
        return min(Decimal(str(self.amount_off)), subtotal)

