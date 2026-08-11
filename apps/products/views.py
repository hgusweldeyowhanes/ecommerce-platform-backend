from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsAdminOrReadOnly

from .filters import ProductFilter
from .models import Category, Product
from .selectors import product_list_qs
from .serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductWriteSerializer,
)
from . import services


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    search_fields = ("name",)


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = ProductFilter
    search_fields = ("name", "description", "sku")
    ordering_fields = ("price", "created_at", "name")
    lookup_field = "slug"

    def get_queryset(self):
        qs = product_list_qs()
        if self.request.user.is_staff:
            qs = Product.objects.select_related("category", "inventory").all()
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def perform_create(self, serializer):
        stock = int(self.request.data.get("initial_stock", 0) or 0)
        product = services.create_product(data=serializer.validated_data, initial_stock=stock)
        serializer.instance = product

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def featured(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(is_featured=True))
        page = self.paginate_queryset(qs)
        ser = ProductListSerializer(page or qs, many=True, context={"request": request})
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)
