from django.contrib import admin

from .models import WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "user__email", "product__name", "product__sku")
    raw_id_fields = ("user", "product")
