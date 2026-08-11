from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "order", "gateway", "amount", "status", "created_at")
    list_filter = ("gateway", "status")
    search_fields = ("reference", "order__order_number")
