from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.products.models import Product
from apps.inventory.services import ensure_inventory

User = get_user_model()


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="buyer", password="pass12345")
        self.product = Product.objects.create(
            name="Test Item", sku="T-1", price="10.00", is_active=True
        )
        ensure_inventory(self.product, quantity=5)

    def test_add_to_cart_and_checkout_mock(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.post(
            "/api/v1/cart/items/",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        r = self.client.post(
            "/api/v1/orders/checkout/",
            {
                "email": "buyer@example.com",
                "shipping_name": "Buyer One",
                "shipping_line1": "123 St",
                "shipping_city": "City",
                "payment_gateway": "mock",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertIn("order", r.data)
        self.assertIn("payment", r.data)
        ref = r.data["payment"]["reference"]
        r2 = self.client.post(f"/api/v1/payments/mock/complete/{ref}/", {}, format="json")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["status"], "success")
