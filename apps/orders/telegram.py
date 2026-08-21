"""Optional Telegram order updates.

Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (or pass chat id per customer later).
"""
import logging
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from django.conf import settings

logger = logging.getLogger(__name__)


def notify(order, text):
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "") or ""
    if not token or not chat_id:
        return
    try:
        body = urlencode({"chat_id": chat_id, "text": text}).encode()
        req = Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            method="POST",
        )
        urlopen(req, timeout=8).read()
    except Exception:
        logger.exception("Telegram notify failed for %s", order.order_number)


def notify_order_placed(order):
    notify(
        order,
        f"Tradiva: new order {order.order_number}\n{order.email}\nTotal {order.currency} {order.total}",
    )


def notify_order_shipped(order):
    notify(
        order,
        f"Tradiva: order {order.order_number} shipped.\n"
        f"Carrier: {order.carrier or '—'}\n"
        f"Tracking: {order.tracking_number or '—'}",
    )
