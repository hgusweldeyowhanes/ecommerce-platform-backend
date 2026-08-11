"""Optional async order tasks."""
from celery import shared_task


@shared_task
def generate_invoice_pdf(order_id: int):
    # Placeholder for PDF invoice generation
    return {"order_id": order_id, "status": "queued"}
