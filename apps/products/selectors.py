from django.db.models import Prefetch

from .models import Category, Product


def product_list_qs():
    return (
        Product.objects.filter(is_active=True)
        .select_related("category", "inventory")
        .all()
    )


def product_by_slug(slug: str):
    return (
        Product.objects.filter(is_active=True, slug=slug)
        .select_related("category", "inventory")
        .first()
    )


def list_categories():
    return Category.objects.filter(is_active=True)
