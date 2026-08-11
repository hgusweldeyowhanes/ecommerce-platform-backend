from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("subject", "email", "channel", "is_sent", "created_at")
    list_filter = ("channel", "is_sent")
