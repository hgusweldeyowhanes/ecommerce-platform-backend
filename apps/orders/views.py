from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.services import initiate_payment
from common.exceptions import ServiceError

from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer
from . import services


class CheckoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = CheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            order = services.create_order_from_cart(request, ser.validated_data)
            payment = initiate_payment(
                order, gateway=ser.validated_data.get("payment_gateway", "mock")
            )
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(
            {
                "order": OrderSerializer(order).data,
                "payment": payment,
            },
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
            return Response({"detail": e.message}, status=400)
        return Response(OrderSerializer(order).data)
