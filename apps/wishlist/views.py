from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.serializers import CartSerializer
from common.exceptions import ServiceError

from .serializers import ProductIdSerializer, WishlistSerializer
from . import services


def _payload(user, request):
    items = list(services.queryset_for(user))
    return WishlistSerializer(
        {"items": items, "item_count": len(items)},
        context={"request": request},
    ).data


class WishlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(_payload(request.user, request))


class WishlistItemAddView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ProductIdSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            _item, created = services.add_item(request.user, ser.validated_data["product_id"])
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        body = _payload(request.user, request)
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class WishlistToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ProductIdSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            in_wishlist = services.toggle_item(request.user, ser.validated_data["product_id"])
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        body = _payload(request.user, request)
        body["in_wishlist"] = in_wishlist
        return Response(body)


class WishlistItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, item_id):
        try:
            services.remove_item(request.user, item_id)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(_payload(request.user, request))


class WishlistMoveToCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, item_id):
        try:
            cart = services.move_to_cart(request, item_id)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(
            {
                "wishlist": _payload(request.user, request),
                "cart": CartSerializer(cart, context={"request": request}).data,
            }
        )
