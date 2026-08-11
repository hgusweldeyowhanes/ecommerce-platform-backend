from django.db import transaction

from apps.orders.services import mark_order_paid
from common.constants import PAYMENT_STATUS_FAILED, PAYMENT_STATUS_SUCCESS
from common.exceptions import ServiceError

from .gateways import get_gateway
from .models import Payment


def initiate_payment(order, gateway: str = "mock") -> dict:
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
    payment = Payment.objects.select_for_update().select_related("order").filter(
        reference=reference
    ).first()
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
