from .models import InventoryItem


def list_inventory():
    return InventoryItem.objects.select_related("product").all()


def inventory_for_product(product_id):
    return InventoryItem.objects.filter(product_id=product_id).first()
