from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_notification_email(notification_id: int):
    from .models import Notification

    note = Notification.objects.filter(pk=notification_id).first()
    if not note or not note.email:
        return False
    send_mail(
        note.subject,
        note.body,
        settings.DEFAULT_FROM_EMAIL,
        [note.email],
        fail_silently=True,
    )
    note.is_sent = True
    note.save(update_fields=["is_sent"])
    return True
