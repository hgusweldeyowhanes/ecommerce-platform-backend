from django.urls import path

from .views import CartItemAddView, CartItemUpdateView, CartView

urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemAddView.as_view(), name="cart-add"),
    path("items/<int:item_id>/", CartItemUpdateView.as_view(), name="cart-item"),
]
