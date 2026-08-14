from django.conf import settings
from django.db import transaction

from apps.orders.services import mark_order_paid, refund_order
from common.constants import PAYMENT_STATUS_FAILED, PAYMENT_STATUS_REFUNDED, PAYMENT_STATUS_SUCCESS
from common.exceptions import ServiceError

from .gateways import get_gateway
from .models import Payment, WebhookEvent


def initiate_payment(order, gateway: str = None) -> dict:
    gateway = (gateway or getattr(settings, "DEFAULT_PAYMENT_GATEWAY", "mock")).lower()
    if gateway == "mock" and not getattr(settings, "ALLOW_MOCK_PAYMENTS", True):
        raise ServiceError("Mock payments are disabled in this environment", code="gateway_disabled")
    gw = get_gateway(gateway)
    payment = Payment.objects.create(
        order=order,
        gateway=gw.name,
        amount=order.total,
        currency=order.currency,
    )
    result = gw.create_checkout(payment, order)
    payment.checkout_url = result.get("checkout_url", "")
    payment.gateway_payment_id = result.get("gateway_payment_id", "")
    payment.raw_response = result.get("raw", {})
    payment.save()
    return {
        "reference": payment.reference,
        "gateway": payment.gateway,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "checkout_url": payment.checkout_url,
    }


@transaction.atomic
def complete_payment(reference: str, success: bool = True) -> Payment:
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(reference=reference)
        .first()
    )
    if not payment:
        raise ServiceError("Payment not found", code="not_found")
    if payment.status == PAYMENT_STATUS_SUCCESS:
        return payment
    if success:
        payment.status = PAYMENT_STATUS_SUCCESS
        payment.save(update_fields=["status", "updated_at"])
        mark_order_paid(payment.order)
    else:
        payment.status = PAYMENT_STATUS_FAILED
        payment.save(update_fields=["status", "updated_at"])
    return payment


@transaction.atomic
def refund_payment(reference: str) -> Payment:
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(reference=reference)
        .first()
    )
    if not payment:
        raise ServiceError("Payment not found", code="not_found")
    if payment.status == PAYMENT_STATUS_REFUNDED:
        return payment
    if payment.status != PAYMENT_STATUS_SUCCESS:
        raise ServiceError("Only successful payments can be refunded", code="invalid_status")
    refund_order(payment.order)
    payment.status = PAYMENT_STATUS_REFUNDED
    payment.save(update_fields=["status", "updated_at"])
    return payment


def record_webhook_event(provider: str, event_id: str, payload: dict) -> bool:
    """Return True if this event is new and should be processed."""
    if not event_id:
        return True
    _, created = WebhookEvent.objects.get_or_create(
        event_id=f"{provider}:{event_id}",
        defaults={"provider": provider, "payload": payload or {}, "processed": True},
    )
    return created
