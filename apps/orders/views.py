from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.services import initiate_payment, refund_payment
from common.exceptions import ServiceError
from common.throttles import CheckoutThrottle

from .models import Coupon, Order
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


class CouponValidateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        code = (request.data.get("code") or "").strip()
        subtotal = request.data.get("subtotal") or 0
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if not coupon or not coupon.is_valid(subtotal):
            return Response({"valid": False, "detail": "Invalid or expired coupon"}, status=400)
        return Response(
            {
                "valid": True,
                "code": coupon.code,
                "percent_off": coupon.percent_off,
                "amount_off": str(coupon.amount_off),
                "discount": str(coupon.compute_discount(subtotal)),
            }
        )


class DashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from django.db.models import Sum, Count
        from decimal import Decimal

        paid = Order.objects.exclude(status__in=["cancelled", "pending"])
        return Response(
            {
                "orders": Order.objects.count(),
                "paid_orders": Order.objects.filter(status="paid").count(),
                "shipped": Order.objects.filter(status="shipped").count(),
                "revenue": str(paid.aggregate(s=Sum("total"))["s"] or Decimal("0")),
                "by_status": list(
                    Order.objects.values("status").annotate(count=Count("id")).order_by("status")
                ),
                "recent": OrderSerializer(Order.objects.prefetch_related("items")[:12], many=True).data,
            }
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

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def refund(self, request, order_number=None):
        order = self.get_object()
        payment = order.payments.order_by("-created_at").first() if hasattr(order, "payments") else None
        try:
            if payment:
                refund_payment(payment.reference)
            else:
                services.refund_order(order)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)
