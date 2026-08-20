from django.db import transaction

from apps.cart.services import add_item as add_cart_item
from apps.cart.services import get_or_create_cart
from apps.products.models import Product
from common.exceptions import ServiceError

from .models import WishlistItem


def queryset_for(user):
    return WishlistItem.objects.filter(user=user).select_related(
        "product", "product__category", "product__inventory"
    )


def add_item(user, product_id):
    product = Product.objects.filter(pk=product_id, is_active=True).first()
    if not product:
        raise ServiceError("Product not found", code="not_found")
    item, created = WishlistItem.objects.get_or_create(user=user, product=product)
    return item, created


def remove_item(user, item_id):
    deleted, _ = WishlistItem.objects.filter(user=user, pk=item_id).delete()
    if not deleted:
        raise ServiceError("Wishlist item not found", code="not_found")


def toggle_item(user, product_id):
    existing = WishlistItem.objects.filter(user=user, product_id=product_id).first()
    if existing:
        existing.delete()
        return False
    add_item(user, product_id)
    return True


@transaction.atomic
def move_to_cart(request, item_id):
    item = (
        WishlistItem.objects.filter(user=request.user, pk=item_id)
        .select_related("product")
        .first()
    )
    if not item:
        raise ServiceError("Wishlist item not found", code="not_found")
    cart = get_or_create_cart(request)
    add_cart_item(cart, item.product_id, 1)
    item.delete()
    return cart
