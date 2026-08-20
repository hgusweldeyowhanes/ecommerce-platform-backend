from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.health import liveness, readiness


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response(
        {
            "service": "ecommerce-platform",
            "version": "v1",
            "health": "/health/",
            "ready": "/health/ready/",
            "endpoints": {
                "auth": "/api/v1/auth/",
                "products": "/api/v1/products/",
                "cart": "/api/v1/cart/",
                "orders": "/api/v1/orders/",
                "payments": "/api/v1/payments/",
                "reviews": "/api/v1/reviews/",
                "inventory": "/api/v1/inventory/",
                "notifications": "/api/v1/notifications/",
                "wishlist": "/api/v1/wishlist/",
            },
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", liveness, name="health-live"),
    path("health/live/", liveness, name="health-live-alias"),
    path("health/ready/", readiness, name="health-ready"),
    path("api/v1/", api_root, name="api-root"),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/cart/", include("apps.cart.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/reviews/", include("apps.reviews.urls")),
    path("api/v1/inventory/", include("apps.inventory.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/wishlist/", include("apps.wishlist.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
