from django.contrib import admin

from .models import Coupon, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "email", "status", "total", "coupon_code", "created_at")
    list_filter = ("status",)
    search_fields = ("order_number", "email")
    inlines = [OrderItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent_off", "amount_off", "is_active", "times_used", "max_uses")
    search_fields = ("code",)
