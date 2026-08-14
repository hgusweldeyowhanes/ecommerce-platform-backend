from django.contrib import admin

from .models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "order", "gateway", "amount", "status", "created_at")
    list_filter = ("gateway", "status")
    search_fields = ("reference", "order__order_number")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_id", "processed", "created_at")
    list_filter = ("provider", "processed")
    search_fields = ("event_id",)
