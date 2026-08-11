"""Stripe payment gateway adapter."""
from django.conf import settings

from common.exceptions import ServiceError


class StripeGateway:
    name = "stripe"

    def create_checkout(self, payment, order, **kwargs):
        if not settings.STRIPE_SECRET_KEY:
            # Fallback-style init for local dev without keys
            return {
                "checkout_url": f"/api/v1/payments/mock/complete/{payment.reference}/",
                "gateway_payment_id": f"stripe_pending_{payment.reference}",
                "raw": {"warning": "STRIPE_SECRET_KEY not set; using mock complete URL"},
            }
        try:
            import stripe

            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.create(
                mode="payment",
                success_url=settings.PAYMENT_SUCCESS_URL
                + f"?ref={payment.reference}",
                cancel_url=settings.PAYMENT_CANCEL_URL,
                customer_email=order.email,
                line_items=[
                    {
                        "price_data": {
                            "currency": order.currency.lower(),
                            "product_data": {"name": f"Order {order.order_number}"},
                            "unit_amount": int(float(order.total) * 100),
                        },
                        "quantity": 1,
                    }
                ],
                metadata={"payment_reference": payment.reference},
            )
            return {
                "checkout_url": session.url,
                "gateway_payment_id": session.id,
                "raw": {"id": session.id},
            }
        except Exception as e:
            raise ServiceError(f"Stripe error: {e}", code="stripe_error") from e

    def verify(self, payment, payload=None):
        return bool(payment.gateway_payment_id)
