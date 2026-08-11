"""Chapa (Ethiopia) payment gateway adapter."""
import requests
from django.conf import settings

from common.exceptions import ServiceError


class ChapaGateway:
    name = "chapa"
    BASE = "https://api.chapa.co/v1"

    def create_checkout(self, payment, order, **kwargs):
        if not settings.CHAPA_SECRET_KEY:
            return {
                "checkout_url": f"/api/v1/payments/mock/complete/{payment.reference}/",
                "gateway_payment_id": f"chapa_pending_{payment.reference}",
                "raw": {"warning": "CHAPA_SECRET_KEY not set; using mock complete URL"},
            }
        try:
            resp = requests.post(
                f"{self.BASE}/transaction/initialize",
                headers={
                    "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "amount": str(order.total),
                    "currency": order.currency if order.currency != "USD" else "ETB",
                    "email": order.email,
                    "first_name": order.shipping_name.split()[0],
                    "last_name": " ".join(order.shipping_name.split()[1:]) or "Customer",
                    "tx_ref": payment.reference,
                    "callback_url": settings.PAYMENT_SUCCESS_URL,
                    "return_url": settings.PAYMENT_SUCCESS_URL,
                    "customization": {
                        "title": "Order Payment",
                        "description": order.order_number,
                    },
                },
                timeout=30,
            )
            data = resp.json()
            if resp.status_code >= 400:
                raise ServiceError(
                    data.get("message", "Chapa init failed"), code="chapa_error"
                )
            checkout = data.get("data", {}).get("checkout_url", "")
            return {
                "checkout_url": checkout,
                "gateway_payment_id": payment.reference,
                "raw": data,
            }
        except ServiceError:
            raise
        except Exception as e:
            raise ServiceError(f"Chapa error: {e}", code="chapa_error") from e

    def verify(self, payment, payload=None):
        if not settings.CHAPA_SECRET_KEY:
            return True
        try:
            resp = requests.get(
                f"{self.BASE}/transaction/verify/{payment.reference}",
                headers={"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"},
                timeout=30,
            )
            data = resp.json()
            status = (data.get("data") or {}).get("status", "")
            return status == "success"
        except Exception:
            return False
