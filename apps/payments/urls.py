from django.urls import path

from .views import (
    ChapaWebhookView,
    MockCompleteView,
    PaymentDetailView,
    StripeWebhookView,
)

urlpatterns = [
    path(
        "mock/complete/<str:reference>/",
        MockCompleteView.as_view(),
        name="payment-mock-complete",
    ),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("webhooks/chapa/", ChapaWebhookView.as_view(), name="chapa-webhook"),
    path("<str:reference>/", PaymentDetailView.as_view(), name="payment-detail"),
]
