from django.urls import path

from .views import (
    WishlistItemAddView,
    WishlistItemView,
    WishlistMoveToCartView,
    WishlistToggleView,
    WishlistView,
)

urlpatterns = [
    path("", WishlistView.as_view(), name="wishlist"),
    path("items/", WishlistItemAddView.as_view(), name="wishlist-add"),
    path("toggle/", WishlistToggleView.as_view(), name="wishlist-toggle"),
    path("items/<int:item_id>/", WishlistItemView.as_view(), name="wishlist-item"),
    path(
        "items/<int:item_id>/move-to-cart/",
        WishlistMoveToCartView.as_view(),
        name="wishlist-move-to-cart",
    ),
]
