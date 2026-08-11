from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.inventory.services import ensure_inventory
from apps.products.models import Category, Product


class Command(BaseCommand):
    help = "Seed demo categories and products"

    def handle(self, *args, **options):
        cat_map = {}
        for name in ("Electronics", "Fashion", "Home"):
            cat, _ = Category.objects.get_or_create(
                slug=name.lower(), defaults={"name": name}
            )
            cat_map[name] = cat

        catalog = [
            ("Wireless Earbuds", "Electronics", "EB-001", "49.99", 40),
            ("Smart Watch", "Electronics", "SW-002", "129.00", 25),
            ("Cotton Tee", "Fashion", "CT-010", "19.50", 100),
            ("Running Shoes", "Fashion", "RS-011", "89.00", 30),
            ("Desk Lamp", "Home", "DL-020", "34.00", 50),
            ("Ceramic Mug", "Home", "CM-021", "12.00", 80),
        ]
        created = 0
        for name, cat_name, sku, price, stock in catalog:
            prod, was = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": name,
                    "category": cat_map[cat_name],
                    "price": Decimal(price),
                    "description": f"Demo product: {name}",
                    "is_active": True,
                    "is_featured": created < 3,
                },
            )
            ensure_inventory(prod, quantity=stock if was else 0)
            if was:
                inv = prod.inventory
                if inv.quantity == 0:
                    inv.quantity = stock
                    inv.save(update_fields=["quantity"])
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Catalog ready ({Product.objects.count()} products)")
        )
