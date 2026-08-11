from django.conf import settings
from django.core.mail import send_mail

from .models import Notification
from .tasks import send_notification_email


def notify_order_placed(order):
    subject = f"Order {order.order_number} received"
    body = (
        f"Thanks for your order {order.order_number}.\n"
        f"Total: {order.currency} {order.total}\n"
        f"Status: {order.status}\n"
    )
    note = Notification.objects.create(
        user=order.user,
        email=order.email,
        subject=subject,
        body=body,
        channel=Notification.CHANNEL_EMAIL,
    )
    # Eager or async depending on Celery settings
    try:
        send_notification_email.delay(note.pk)
    except Exception:
        _send_sync(note)
    return note


def _send_sync(note: Notification):
    try:
        send_mail(
            note.subject,
            note.body,
            settings.DEFAULT_FROM_EMAIL,
            [note.email],
            fail_silently=True,
        )
        note.is_sent = True
        note.save(update_fields=["is_sent"])
    except Exception:
        pass
