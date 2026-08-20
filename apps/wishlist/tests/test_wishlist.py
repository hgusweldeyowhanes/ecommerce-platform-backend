from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.inventory.services import ensure_inventory
from apps.products.models import Product

User = get_user_model()


class WishlistTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="saver", password="pass12345")
        self.product = Product.objects.create(
            name="Saved Tee", sku="W-1", price="19.00", is_active=True
        )
        ensure_inventory(self.product, quantity=4)

    def test_guest_cannot_list(self):
        r = self.client.get("/api/v1/wishlist/")
        self.assertIn(r.status_code, (401, 403))

    def test_add_toggle_and_move_to_cart(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.post(
            "/api/v1/wishlist/items/",
            {"product_id": self.product.id},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["item_count"], 1)
        item_id = r.data["items"][0]["id"]

        r = self.client.post(
            "/api/v1/wishlist/items/",
            {"product_id": self.product.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["item_count"], 1)

        r = self.client.post(
            "/api/v1/wishlist/toggle/",
            {"product_id": self.product.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["in_wishlist"])
        self.assertEqual(r.data["item_count"], 0)

        r = self.client.post(
            "/api/v1/wishlist/toggle/",
            {"product_id": self.product.id},
            format="json",
        )
        self.assertTrue(r.data["in_wishlist"])
        item_id = r.data["items"][0]["id"]

        r = self.client.post(f"/api/v1/wishlist/items/{item_id}/move-to-cart/", {}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["wishlist"]["item_count"], 0)
        self.assertEqual(r.data["cart"]["item_count"], 1)
