from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import ServiceError

from .serializers import CartItemWriteSerializer, CartSerializer
from . import services


class CartView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cart = services.get_or_create_cart(request)
        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        cart = services.get_or_create_cart(request)
        services.clear_cart(cart)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemAddView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = CartItemWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cart = services.get_or_create_cart(request)
        try:
            services.add_item(
                cart,
                ser.validated_data["product_id"],
                ser.validated_data.get("quantity", 1),
            )
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        cart = services.get_or_create_cart(request)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartItemUpdateView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, item_id):
        qty = int(request.data.get("quantity", 1))
        cart = services.get_or_create_cart(request)
        try:
            services.update_item(cart, item_id, qty)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request, item_id):
        cart = services.get_or_create_cart(request)
        services.remove_item(cart, item_id)
        return Response(CartSerializer(cart, context={"request": request}).data)
