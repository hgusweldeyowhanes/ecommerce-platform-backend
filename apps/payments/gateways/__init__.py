"""Payment gateway adapters."""
from .chapa import ChapaGateway
from .stripe import StripeGateway


class MockGateway:
    name = "mock"

    def create_checkout(self, payment, order, **kwargs):
        return {
            "checkout_url": f"/api/v1/payments/mock/complete/{payment.reference}/",
            "gateway_payment_id": f"mock_{payment.reference}",
            "raw": {"mode": "mock"},
        }

    def verify(self, payment, payload=None):
        return True


def get_gateway(name: str):
    name = (name or "mock").lower()
    if name == "stripe":
        return StripeGateway()
    if name == "chapa":
        return ChapaGateway()
    return MockGateway()
