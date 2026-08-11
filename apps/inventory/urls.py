from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import InventoryViewSet, ProductMovementsView, StockAdjustView

router = DefaultRouter()
router.register(r"", InventoryViewSet, basename="inventory")

urlpatterns = router.urls + [
    path("adjust/", StockAdjustView.as_view(), name="stock-adjust"),
    path(
        "products/<int:product_id>/movements/",
        ProductMovementsView.as_view(),
        name="stock-movements",
    ),
]
