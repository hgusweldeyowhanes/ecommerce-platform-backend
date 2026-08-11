from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from common.exceptions import ServiceError

from .models import InventoryItem
from .serializers import InventorySerializer, StockAdjustSerializer, StockMovementSerializer
from . import services


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryItem.objects.select_related("product").all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAdminUser]
    search_fields = ("product__name", "product__sku")


class StockAdjustView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        ser = StockAdjustSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        product = Product.objects.filter(pk=ser.validated_data["product_id"]).first()
        if not product:
            return Response({"detail": "Product not found"}, status=404)
        try:
            inv = services.adjust_stock(
                product,
                ser.validated_data["delta"],
                note=ser.validated_data.get("note", ""),
            )
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(InventorySerializer(inv).data)


class ProductMovementsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, product_id):
        inv = InventoryItem.objects.filter(product_id=product_id).first()
        if not inv:
            return Response([])
        moves = inv.movements.all()[:50]
        return Response(StockMovementSerializer(moves, many=True).data)
