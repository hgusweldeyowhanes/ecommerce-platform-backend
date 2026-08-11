import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    category = django_filters.CharFilter(field_name="category__slug")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ("is_featured", "category", "currency")

    def filter_in_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(inventory__quantity__gt=0)
        if value is False:
            return queryset.filter(inventory__quantity__lte=0)
        return queryset
