from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.services import initiate_payment
from common.exceptions import ServiceError
from common.throttles import CheckoutThrottle

from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer
from . import services


class CheckoutView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [CheckoutThrottle]

    def post(self, request):
        ser = CheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        gateway = data.get("payment_gateway") or settings.DEFAULT_PAYMENT_GATEWAY
        try:
            order = services.create_order_from_cart(request, data)
            payment = initiate_payment(order, gateway=gateway)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(
            {"order": OrderSerializer(order).data, "payment": payment},
            status=status.HTTP_201_CREATED,
        )


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "order_number"

    def get_queryset(self):
        qs = Order.objects.prefetch_related("items")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def cancel(self, request, order_number=None):
        order = self.get_object()
        try:
            order = services.cancel_order(order)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def ship(self, request, order_number=None):
        order = self.get_object()
        try:
            order = services.ship_order(
                order,
                tracking_number=request.data.get("tracking_number", ""),
                carrier=request.data.get("carrier", ""),
            )
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def deliver(self, request, order_number=None):
        order = self.get_object()
        try:
            order = services.deliver_order(order)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(OrderSerializer(order).data)
