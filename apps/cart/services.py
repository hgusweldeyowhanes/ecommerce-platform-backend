from django.db import transaction

from apps.inventory.services import ensure_inventory
from apps.products.models import Product, ProductVariant
from common.exceptions import ServiceError

from .models import Cart, CartItem


def _ensure_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request) -> Cart:
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
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
        existing = target.items.filter(product=item.product, variant=item.variant).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity"])
        else:
            item.cart = target
            item.save(update_fields=["cart"])
    source.delete()


def _available(product, variant=None):
    if variant is not None:
        return variant.stock if variant.is_active else 0
    inv = ensure_inventory(product)
    return inv.available


@transaction.atomic
def add_item(cart: Cart, product_id: int, quantity: int = 1, variant_id: int = None) -> CartItem:
    product = Product.objects.filter(pk=product_id, is_active=True).first()
    if not product:
        raise ServiceError("Product not found", code="not_found")
    variant = None
    if variant_id:
        variant = ProductVariant.objects.filter(
            pk=variant_id, product=product, is_active=True
        ).first()
        if not variant:
            raise ServiceError("Variant not found", code="not_found")
    elif product.variants.filter(is_active=True).exists():
        raise ServiceError("Choose a product option", code="variant_required")

    if _available(product, variant) < quantity:
        raise ServiceError("Insufficient stock", code="out_of_stock")

    unit_price = variant.effective_price if variant else product.price
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={"quantity": quantity, "unit_price": unit_price},
    )
    if not created:
        new_qty = item.quantity + quantity
        if _available(product, variant) < new_qty:
            raise ServiceError("Insufficient stock", code="out_of_stock")
        item.quantity = new_qty
        item.unit_price = unit_price
        item.save()
    return item


@transaction.atomic
def update_item(cart: Cart, item_id: int, quantity: int) -> CartItem:
    item = (
        CartItem.objects.filter(cart=cart, pk=item_id)
        .select_related("product", "variant")
        .first()
    )
    if not item:
        raise ServiceError("Cart item not found", code="not_found")
    if quantity <= 0:
        item.delete()
        return None
    if _available(item.product, item.variant) < quantity:
        raise ServiceError("Insufficient stock", code="out_of_stock")
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return item


def remove_item(cart: Cart, item_id: int) -> None:
    CartItem.objects.filter(cart=cart, pk=item_id).delete()


def clear_cart(cart: Cart) -> None:
    cart.items.all().delete()
