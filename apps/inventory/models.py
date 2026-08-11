from decimal import Decimal

from django.db import models

from apps.products.models import Product
from common.constants import (
    STOCK_MOVE_IN,
    STOCK_MOVE_OUT,
    STOCK_MOVE_RELEASE,
    STOCK_MOVE_RESERVE,
)


class InventoryItem(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "inventory items"

    def __str__(self):
        return f"{self.product.sku}: {self.available} available"

    @property
    def available(self) -> int:
        return max(self.quantity - self.reserved, 0)


class StockMovement(models.Model):
    MOVE_TYPES = [
        (STOCK_MOVE_IN, "Stock in"),
        (STOCK_MOVE_OUT, "Stock out"),
        (STOCK_MOVE_RESERVE, "Reserve"),
        (STOCK_MOVE_RELEASE, "Release"),
    ]

    inventory = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="movements"
    )
    move_type = models.CharField(max_length=16, choices=MOVE_TYPES)
    quantity = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]
