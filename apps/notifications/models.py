from django.conf import settings
from django.db import models


class Notification(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_INAPP = "in_app"
    CHANNELS = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_INAPP, "In-app"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    email = models.EmailField(blank=True)
    channel = models.CharField(max_length=16, choices=CHANNELS, default=CHANNEL_EMAIL)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_sent = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
