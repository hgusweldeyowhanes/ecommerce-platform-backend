from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.cart import services as cart_services
from apps.cart.models import Cart
from apps.inventory.services import commit_reservation, release_reservation, reserve_stock
from apps.notifications.services import notify_order_placed
from common.constants import ORDER_STATUS_CANCELLED, ORDER_STATUS_PAID, ORDER_STATUS_PENDING
from common.exceptions import ServiceError

from .models import Order, OrderItem


@transaction.atomic
def create_order_from_cart(request, checkout_data: dict) -> Order:
    cart = cart_services.get_or_create_cart(request)
    items = list(cart.items.select_related("product"))
    if not items:
        raise ServiceError("Cart is empty", code="empty_cart")

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        email=checkout_data["email"],
        status=ORDER_STATUS_PENDING,
        shipping_name=checkout_data["shipping_name"],
        shipping_line1=checkout_data["shipping_line1"],
        shipping_line2=checkout_data.get("shipping_line2", ""),
        shipping_city=checkout_data["shipping_city"],
        shipping_state=checkout_data.get("shipping_state", ""),
        shipping_postal_code=checkout_data.get("shipping_postal_code", ""),
        shipping_country=checkout_data.get("shipping_country", "US"),
        shipping_phone=checkout_data.get("shipping_phone", ""),
        notes=checkout_data.get("notes", ""),
        shipping_fee=Decimal(str(checkout_data.get("shipping_fee") or 0)),
        currency=items[0].product.currency if items else "USD",
    )

    reserved = []
    try:
        for ci in items:
            reserve_stock(ci.product, ci.quantity, reference=order.order_number)
            reserved.append((ci.product, ci.quantity))
            OrderItem.objects.create(
                order=order,
                product=ci.product,
                product_name=ci.product.name,
                sku=ci.product.sku,
                unit_price=ci.unit_price,
                quantity=ci.quantity,
                line_total=ci.line_total,
            )
    except ServiceError:
        for product, qty in reserved:
            release_reservation(product, qty, reference=order.order_number)
        order.delete()
        raise

    order.shipping_fee = Decimal(str(checkout_data.get("shipping_fee") or 0))
    order.recompute_totals()
    cart_services.clear_cart(cart)
    notify_order_placed(order)
    return order


@transaction.atomic
def mark_order_paid(order: Order) -> Order:
    if order.status == ORDER_STATUS_PAID:
        return order
    for item in order.items.select_related("product"):
        if item.product_id:
            commit_reservation(item.product, item.quantity, reference=order.order_number)
    order.status = ORDER_STATUS_PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at", "updated_at"])
    return order


@transaction.atomic
def cancel_order(order: Order) -> Order:
    if order.status in (ORDER_STATUS_CANCELLED, ORDER_STATUS_PAID):
        if order.status == ORDER_STATUS_PAID:
            raise ServiceError("Paid orders cannot be cancelled here", code="invalid_status")
    if order.status == ORDER_STATUS_PENDING:
        for item in order.items.select_related("product"):
            if item.product_id:
                release_reservation(
                    item.product, item.quantity, reference=order.order_number
                )
    order.status = ORDER_STATUS_CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order
