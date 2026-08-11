from .models import Order


def user_orders(user):
    return Order.objects.filter(user=user).prefetch_related("items")


def order_by_number(order_number: str):
    return Order.objects.filter(order_number=order_number).prefetch_related("items").first()
