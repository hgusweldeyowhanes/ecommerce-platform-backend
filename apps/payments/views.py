from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import ServiceError

from .models import Payment
from .serializers import PaymentSerializer
from . import services


class PaymentDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, reference):
        payment = Payment.objects.filter(reference=reference).select_related("order").first()
        if not payment:
            return Response({"detail": "Not found"}, status=404)
        return Response(PaymentSerializer(payment).data)


class MockCompleteView(APIView):
    """Local/dev completion endpoint when real gateway keys are missing."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, reference):
        success = request.data.get("success", True)
        try:
            payment = services.complete_payment(reference, success=bool(success))
        except ServiceError as e:
            return Response({"detail": e.message}, status=400)
        return Response(PaymentSerializer(payment).data)

    def get(self, request, reference):
        # Allow browser redirect completion
        try:
            payment = services.complete_payment(reference, success=True)
        except ServiceError as e:
            return Response({"detail": e.message}, status=400)
        return Response(PaymentSerializer(payment).data)


class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        # Minimal webhook stub — expand with stripe.Webhook.construct_event in prod
        ref = request.data.get("data", {}).get("object", {}).get("metadata", {}).get(
            "payment_reference"
        )
        if ref:
            services.complete_payment(ref, success=True)
        return Response({"received": True})


class ChapaWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        ref = request.data.get("tx_ref") or request.data.get("reference")
        status_str = (request.data.get("status") or "").lower()
        if ref:
            services.complete_payment(ref, success=status_str in ("success", "successful"))
        return Response({"received": True})
