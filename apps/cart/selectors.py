from .models import Cart


def get_user_cart(user):
    return Cart.objects.filter(user=user).prefetch_related("items__product").first()
