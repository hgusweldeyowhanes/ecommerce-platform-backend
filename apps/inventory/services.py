from django.db import transaction
from django.db.models import F

from common.constants import (
    STOCK_MOVE_IN,
    STOCK_MOVE_OUT,
    STOCK_MOVE_RELEASE,
    STOCK_MOVE_RESERVE,
)
from common.exceptions import ServiceError

from .models import InventoryItem, StockMovement


def ensure_inventory(product, quantity: int = 0) -> InventoryItem:
    inv, _ = InventoryItem.objects.get_or_create(
        product=product, defaults={"quantity": quantity}
    )
    return inv


@transaction.atomic
def adjust_stock(product, delta: int, note: str = "", reference: str = "") -> InventoryItem:
    inv = ensure_inventory(product)
    inv = InventoryItem.objects.select_for_update().get(pk=inv.pk)
    new_qty = inv.quantity + delta
    if new_qty < 0:
        raise ServiceError("Insufficient stock", code="out_of_stock")
    inv.quantity = new_qty
    inv.save(update_fields=["quantity", "updated_at"])
    move = STOCK_MOVE_IN if delta >= 0 else STOCK_MOVE_OUT
    StockMovement.objects.create(
        inventory=inv,
        move_type=move,
        quantity=abs(delta),
        note=note,
        reference=reference,
    )
    return inv


@transaction.atomic
def reserve_stock(product, qty: int, reference: str = "") -> InventoryItem:
    inv = ensure_inventory(product)
    inv = InventoryItem.objects.select_for_update().get(pk=inv.pk)
    if inv.available < qty:
        raise ServiceError(
            f"Not enough stock for {product.sku}", code="out_of_stock"
        )
    inv.reserved = F("reserved") + qty
    inv.save(update_fields=["reserved", "updated_at"])
    inv.refresh_from_db()
    StockMovement.objects.create(
        inventory=inv,
        move_type=STOCK_MOVE_RESERVE,
        quantity=qty,
        reference=reference,
    )
    return inv


@transaction.atomic
def release_reservation(product, qty: int, reference: str = "") -> InventoryItem:
    inv = ensure_inventory(product)
    inv = InventoryItem.objects.select_for_update().get(pk=inv.pk)
    inv.reserved = max(inv.reserved - qty, 0)
    inv.save(update_fields=["reserved", "updated_at"])
    StockMovement.objects.create(
        inventory=inv,
        move_type=STOCK_MOVE_RELEASE,
        quantity=qty,
        reference=reference,
    )
    return inv


@transaction.atomic
def commit_reservation(product, qty: int, reference: str = "") -> InventoryItem:
    """Convert reserved units into sold stock."""
    inv = ensure_inventory(product)
    inv = InventoryItem.objects.select_for_update().get(pk=inv.pk)
    if inv.reserved < qty or inv.quantity < qty:
        raise ServiceError("Cannot commit stock", code="stock_error")
    inv.reserved -= qty
    inv.quantity -= qty
    inv.save(update_fields=["reserved", "quantity", "updated_at"])
    StockMovement.objects.create(
        inventory=inv,
        move_type=STOCK_MOVE_OUT,
        quantity=qty,
        note="Order paid",
        reference=reference,
    )
    return inv


@transaction.atomic
def restock_sold(product, qty: int, reference: str = "") -> InventoryItem:
    """Return sold units after a refund."""
    inv = ensure_inventory(product)
    inv = InventoryItem.objects.select_for_update().get(pk=inv.pk)
    inv.quantity += qty
    inv.save(update_fields=["quantity", "updated_at"])
    StockMovement.objects.create(
        inventory=inv,
        move_type=STOCK_MOVE_IN,
        quantity=qty,
        note="Refund restock",
        reference=reference,
    )
    return inv
