from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.cart import services as cart_services
from apps.products.models import ProductVariant
from apps.inventory.services import (
    commit_reservation,
    release_reservation,
    reserve_stock,
    restock_sold,
)
from apps.notifications.services import notify_order_placed
from common.constants import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_PROCESSING,
    ORDER_STATUS_REFUNDED,
    ORDER_STATUS_SHIPPED,
)
from common.exceptions import ServiceError

from .models import Coupon, Order, OrderItem
from . import telegram as telegram_notify


def _idempotent_order(request, key: str, email: str):
    if not key:
        return None
    qs = Order.objects.all()
    if request.user.is_authenticated:
        return qs.filter(user=request.user, idempotency_key=key).first()
    return qs.filter(user__isnull=True, idempotency_key=key, email=email).first()


@transaction.atomic
def create_order_from_cart(request, checkout_data: dict) -> Order:
    idem_key = (
        request.headers.get("Idempotency-Key")
        or checkout_data.get("idempotency_key")
        or ""
    ).strip()
    existing = _idempotent_order(request, idem_key, checkout_data.get("email", ""))
    if existing:
        return existing

    cart = cart_services.get_or_create_cart(request)
    items = list(cart.items.select_related("product", "variant"))
    if not items:
        raise ServiceError("Cart is empty", code="empty_cart")

    subtotal = sum((ci.line_total for ci in items), Decimal("0"))
    discount = Decimal("0")
    coupon_code = (checkout_data.get("coupon_code") or "").strip().upper()
    coupon = None
    if coupon_code:
        coupon = Coupon.objects.select_for_update().filter(code__iexact=coupon_code).first()
        if not coupon or not coupon.is_valid(subtotal):
            raise ServiceError("Invalid or expired coupon", code="invalid_coupon")
        discount = coupon.compute_discount(subtotal)

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
        currency=items[0].product.currency if items else settings.DEFAULT_CURRENCY,
        coupon_code=coupon_code,
        discount=discount,
        idempotency_key=idem_key,
    )

    reserved = []
    variant_reserved = []
    try:
        for ci in items:
            if ci.variant_id:
                variant = ProductVariant.objects.select_for_update().get(pk=ci.variant_id)
                if variant.stock < ci.quantity:
                    raise ServiceError("Insufficient stock", code="out_of_stock")
                variant.stock -= ci.quantity
                variant.save(update_fields=["stock"])
                variant_reserved.append((variant, ci.quantity))
            else:
                reserve_stock(ci.product, ci.quantity, reference=order.order_number)
                reserved.append((ci.product, ci.quantity))
            OrderItem.objects.create(
                order=order,
                product=ci.product,
                variant=ci.variant,
                product_name=ci.product.name,
                sku=ci.variant.sku if ci.variant_id else ci.product.sku,
                variant_name=ci.variant.name if ci.variant_id else "",
                unit_price=ci.unit_price,
                quantity=ci.quantity,
                line_total=ci.line_total,
            )
    except ServiceError:
        for product, qty in reserved:
            release_reservation(product, qty, reference=order.order_number)
        for variant, qty in variant_reserved:
            variant.stock += qty
            variant.save(update_fields=["stock"])
        order.delete()
        raise

    if coupon:
        coupon.times_used += 1
        coupon.save(update_fields=["times_used"])

    order.recompute_totals()
    cart_services.clear_cart(cart)
    notify_order_placed(order)
    telegram_notify.notify_order_placed(order)
    return order


@transaction.atomic
def mark_order_paid(order: Order) -> Order:
    if order.status == ORDER_STATUS_PAID:
        return order
    for item in order.items.select_related("product", "variant"):
        if item.variant_id:
            continue  # variant stock already deducted at checkout
        if item.product_id:
            commit_reservation(item.product, item.quantity, reference=order.order_number)
    order.status = ORDER_STATUS_PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at", "updated_at"])
    return order


@transaction.atomic
def cancel_order(order: Order) -> Order:
    if order.status == ORDER_STATUS_PAID:
        raise ServiceError(
            "Paid orders cannot be cancelled here; request a refund",
            code="invalid_status",
        )
    if order.status == ORDER_STATUS_CANCELLED:
        return order
    if order.status == ORDER_STATUS_PENDING:
        for item in order.items.select_related("product", "variant"):
            if item.variant_id:
                ProductVariant.objects.filter(pk=item.variant_id).update(
                    stock=models.F("stock") + item.quantity
                )
            elif item.product_id:
                release_reservation(item.product, item.quantity, reference=order.order_number)
    order.status = ORDER_STATUS_CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def ship_order(order: Order, tracking_number: str = "", carrier: str = "") -> Order:
    if order.status not in (ORDER_STATUS_PAID, ORDER_STATUS_PROCESSING):
        raise ServiceError("Only paid orders can be shipped", code="invalid_status")
    order.status = ORDER_STATUS_SHIPPED
    order.tracking_number = tracking_number
    order.carrier = carrier
    order.shipped_at = timezone.now()
    order.save(
        update_fields=["status", "tracking_number", "carrier", "shipped_at", "updated_at"]
    )
    telegram_notify.notify_order_shipped(order)
    return order


@transaction.atomic
def deliver_order(order: Order) -> Order:
    if order.status != ORDER_STATUS_SHIPPED:
        raise ServiceError("Only shipped orders can be marked delivered", code="invalid_status")
    order.status = ORDER_STATUS_DELIVERED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def refund_order(order: Order) -> Order:
    if order.status not in (
        ORDER_STATUS_PAID,
        ORDER_STATUS_PROCESSING,
        ORDER_STATUS_SHIPPED,
        ORDER_STATUS_DELIVERED,
    ):
        raise ServiceError("This order cannot be refunded", code="invalid_status")
    for item in order.items.select_related("product", "variant"):
        if item.variant_id:
            ProductVariant.objects.filter(pk=item.variant_id).update(
                stock=models.F("stock") + item.quantity
            )
        elif item.product_id:
            restock_sold(item.product, item.quantity, reference=order.order_number)
    order.status = ORDER_STATUS_REFUNDED
    order.save(update_fields=["status", "updated_at"])
    return order
