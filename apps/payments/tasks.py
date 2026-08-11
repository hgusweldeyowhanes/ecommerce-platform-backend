from celery import shared_task

from .services import complete_payment


@shared_task
def reconcile_payment(reference: str):
    return complete_payment(reference, success=True).status
