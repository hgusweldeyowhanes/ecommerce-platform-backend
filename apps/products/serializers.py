from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "is_active")


class ProductListSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "price",
            "compare_at_price",
            "currency",
            "sku",
            "is_active",
            "is_featured",
            "image",
            "category",
            "category_name",
            "stock_quantity",
            "in_stock",
            "created_at",
        )

    def get_stock_quantity(self, obj):
        return obj.stock_quantity

    def get_in_stock(self, obj):
        return obj.in_stock


class ProductDetailSerializer(ProductListSerializer):
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "attributes",
            "updated_at",
        )


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "name",
            "description",
            "price",
            "compare_at_price",
            "currency",
            "sku",
            "category",
            "is_active",
            "is_featured",
            "image",
            "attributes",
        )
