from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "is_active")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text", "sort_order")


class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "name",
            "sku",
            "price",
            "effective_price",
            "stock",
            "options",
            "is_active",
            "in_stock",
        )


class ProductListSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    image = serializers.SerializerMethodField()

    has_variants = serializers.SerializerMethodField()

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
            "has_variants",
            "created_at",
        )

    def get_stock_quantity(self, obj):
        variants = [v for v in obj.variants.all() if v.is_active] if hasattr(obj, "variants") else []
        if variants:
            return sum(v.stock for v in variants)
        return obj.stock_quantity

    def get_in_stock(self, obj):
        return obj.in_stock

    def get_has_variants(self, obj):
        variants = getattr(obj, "variants", None)
        if variants is None:
            return False
        return any(v.is_active for v in variants.all())

    def get_image(self, obj):
        # Relative /media/... URLs so the Vite proxy (and same-origin deploys) serve them.
        if obj.image:
            return obj.image.url
        first = obj.images.first() if hasattr(obj, "images") else None
        if first and first.image:
            return first.image.url
        return None


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    related = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "attributes",
            "updated_at",
            "images",
            "variants",
            "related",
        )

    def get_related(self, obj):
        qs = (
            Product.objects.filter(is_active=True, category=obj.category)
            .exclude(pk=obj.pk)
            .select_related("category", "inventory")
            .prefetch_related("images", "variants")[:4]
        )
        return ProductListSerializer(qs, many=True, context=self.context).data


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
