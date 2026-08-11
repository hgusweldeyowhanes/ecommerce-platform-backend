from django.db import transaction

from apps.inventory.services import ensure_inventory

from .models import Product


@transaction.atomic
def create_product(*, data, initial_stock: int = 0) -> Product:
    product = Product.objects.create(**data)
    ensure_inventory(product, quantity=initial_stock)
    return product


def update_product(product: Product, **data) -> Product:
    for k, v in data.items():
        setattr(product, k, v)
    product.save()
    return product
