from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.inventory.models import InventoryItem
from apps.inventory.services import ensure_inventory
from apps.orders.models import Coupon
from apps.products.models import Product

User = get_user_model()


class HealthTests(TestCase):
    def test_liveness(self):
        r = self.client.get("/health/live/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_readiness(self):
        r = self.client.get("/health/ready/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("database", r.json()["checks"])


class AuthFlowTests(TestCase):
    def test_password_reset(self):
        user = User.objects.create_user(
            username="resetme", email="reset@example.com", password="OldPass123!"
        )
        c = APIClient()
        r = c.post("/api/v1/auth/password/reset/", {"email": "reset@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        r = c.post(
            "/api/v1/auth/password/reset/confirm/",
            {"uid": uid, "token": token, "password": "NewPass123!"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123!"))


class CheckoutAdvancedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="buyer2", password="pass12345")
        self.product = Product.objects.create(
            name="Lamp", sku="L-1", price="20.00", is_active=True
        )
        ensure_inventory(self.product, quantity=10)
        Coupon.objects.create(code="SAVE10", percent_off=10, is_active=True)
        self.client.force_authenticate(user=self.user)

    def test_coupon_and_mock_pay(self):
        self.client.post(
            "/api/v1/cart/items/",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        r = self.client.post(
            "/api/v1/orders/checkout/",
            {
                "email": "buyer2@example.com",
                "shipping_name": "Buyer Two",
                "shipping_line1": "1 St",
                "shipping_city": "Addis",
                "payment_gateway": "mock",
                "coupon_code": "SAVE10",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["order"]["discount"], "4.00")
        ref = r.data["payment"]["reference"]
        paid = self.client.post(f"/api/v1/payments/mock/complete/{ref}/", {}, format="json")
        self.assertEqual(paid.status_code, 200)
        inv = InventoryItem.objects.get(product=self.product)
        self.assertEqual(inv.quantity, 8)

    def test_checkout_idempotency(self):
        self.client.post(
            "/api/v1/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        payload = {
            "email": "buyer2@example.com",
            "shipping_name": "Buyer Two",
            "shipping_line1": "1 St",
            "shipping_city": "Addis",
            "payment_gateway": "mock",
            "idempotency_key": "abc-123",
        }
        r1 = self.client.post("/api/v1/orders/checkout/", payload, format="json")
        r2 = self.client.post("/api/v1/orders/checkout/", payload, format="json")
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.data["order"]["order_number"], r2.data["order"]["order_number"])

    @override_settings(ALLOW_MOCK_PAYMENTS=False)
    def test_mock_complete_disabled(self):
        r = self.client.post("/api/v1/payments/mock/complete/does-not-exist/", {}, format="json")
        self.assertEqual(r.status_code, 403)


class WebhookSecurityTests(TestCase):
    def test_stripe_rejects_bad_signature(self):
        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test"):
            r = self.client.post(
                "/api/v1/payments/webhooks/stripe/",
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="bad",
            )
        self.assertEqual(r.status_code, 400)
