import hashlib
import hmac
import logging

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import ServiceError

from .models import Payment
from .serializers import PaymentSerializer
from . import services

logger = logging.getLogger(__name__)


class PaymentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, reference):
        payment = Payment.objects.filter(reference=reference).select_related("order").first()
        if not payment:
            return Response({"detail": "Not found"}, status=404)
        if not request.user.is_staff:
            if payment.order.user_id != request.user.id:
                return Response({"detail": "Not found"}, status=404)
        return Response(PaymentSerializer(payment).data)


class MockCompleteView(APIView):
    """Local/dev completion endpoint. Disabled when ALLOW_MOCK_PAYMENTS is False."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def _run(self, request, reference, success=True):
        if not getattr(settings, "ALLOW_MOCK_PAYMENTS", False):
            return Response({"detail": "Mock payments are disabled"}, status=403)
        try:
            payment = services.complete_payment(reference, success=bool(success))
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(PaymentSerializer(payment).data)

    def post(self, request, reference):
        success = request.data.get("success", True)
        return self._run(request, reference, success)

    def get(self, request, reference):
        return self._run(request, reference, True)


class RefundView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, reference):
        try:
            payment = services.refund_payment(reference)
        except ServiceError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        return Response(PaymentSerializer(payment).data)


class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser]

    def post(self, request):
        payload = request.body
        sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        secret = settings.STRIPE_WEBHOOK_SECRET
        if not secret:
            logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET is empty")
            return Response({"detail": "webhook not configured"}, status=503)
        try:
            import stripe

            event = stripe.Webhook.construct_event(payload, sig, secret)
        except Exception as exc:
            logger.info("Stripe webhook rejected: %s", exc)
            return Response({"detail": "invalid signature"}, status=400)

        event_id = event.get("id", "")
        if not services.record_webhook_event("stripe", event_id, event):
            return Response({"received": True, "duplicate": True})

        obj = (event.get("data") or {}).get("object") or {}
        ref = (obj.get("metadata") or {}).get("payment_reference")
        etype = event.get("type", "")
        if ref and etype in {"checkout.session.completed", "payment_intent.succeeded"}:
            services.complete_payment(ref, success=True)
        elif ref and etype in {"checkout.session.expired", "payment_intent.payment_failed"}:
            services.complete_payment(ref, success=False)
        return Response({"received": True})


class ChapaWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        secret = settings.CHAPA_WEBHOOK_SECRET or settings.CHAPA_SECRET_KEY
        if not secret:
            logger.warning("Chapa webhook received but secret is empty")
            return Response({"detail": "webhook not configured"}, status=503)
        signature = (
            request.META.get("HTTP_CHAPA_SIGNATURE")
            or request.META.get("HTTP_X_CHAPA_SIGNATURE")
            or ""
        )
        expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        if not signature:
            if settings.DEBUG:
                logger.warning("Chapa webhook with no signature (allowed in DEBUG)")
            else:
                return Response({"detail": "missing signature"}, status=400)
        elif not hmac.compare_digest(signature, expected):
            return Response({"detail": "invalid signature"}, status=400)

        data = request.data if isinstance(request.data, dict) else {}
        ref = data.get("tx_ref") or data.get("reference")
        event_id = data.get("id") or data.get("event") or ref
        if not services.record_webhook_event("chapa", str(event_id or ""), data):
            return Response({"received": True, "duplicate": True})
        status_str = (data.get("status") or "").lower()
        if ref:
            services.complete_payment(ref, success=status_str in ("success", "successful"))
        return Response({"received": True})
