from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CheckoutView, CouponValidateView, DashboardView, OrderViewSet

router = DefaultRouter()
router.register(r"", OrderViewSet, basename="order")

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("coupons/validate/", CouponValidateView.as_view(), name="coupon-validate"),
    path("dashboard/", DashboardView.as_view(), name="staff-dashboard"),
    path("", include(router.urls)),
]
