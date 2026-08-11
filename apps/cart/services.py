from django.db import transaction

from apps.inventory.services import ensure_inventory
from apps.products.models import Product
from common.exceptions import ServiceError

from .models import Cart, CartItem


def _ensure_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request) -> Cart:
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        # merge guest cart if present
        sk = request.session.session_key
        if sk:
            guest = Cart.objects.filter(session_key=sk, user__isnull=True).first()
            if guest and guest.pk != cart.pk:
                merge_carts(cart, guest)
        return cart
    sk = _ensure_session(request)
    cart, _ = Cart.objects.get_or_create(session_key=sk, user=None)
    return cart


@transaction.atomic
def merge_carts(target: Cart, source: Cart):
    for item in source.items.all():
        existing = target.items.filter(product=item.product).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity"])
        else:
            item.cart = target
            item.save(update_fields=["cart"])
    source.delete()


@transaction.atomic
def add_item(cart: Cart, product_id: int, quantity: int = 1) -> CartItem:
    product = Product.objects.filter(pk=product_id, is_active=True).first()
    if not product:
        raise ServiceError("Product not found", code="not_found")
    inv = ensure_inventory(product)
    if inv.available < quantity:
        raise ServiceError("Insufficient stock", code="out_of_stock")
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity, "unit_price": product.price},
    )
    if not created:
        new_qty = item.quantity + quantity
        if inv.available < new_qty:
            raise ServiceError("Insufficient stock", code="out_of_stock")
        item.quantity = new_qty
        item.unit_price = product.price
        item.save()
    return item


@transaction.atomic
def update_item(cart: Cart, item_id: int, quantity: int) -> CartItem:
    item = CartItem.objects.filter(cart=cart, pk=item_id).select_related("product").first()
    if not item:
        raise ServiceError("Cart item not found", code="not_found")
    if quantity <= 0:
        item.delete()
        return None
    inv = ensure_inventory(item.product)
    if inv.available < quantity:
        raise ServiceError("Insufficient stock", code="out_of_stock")
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def remove_item(cart: Cart, item_id: int) -> None:
    CartItem.objects.filter(cart=cart, pk=item_id).delete()


def clear_cart(cart: Cart) -> None:
    cart.items.all().delete()
