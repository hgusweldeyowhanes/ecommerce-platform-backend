import uuid


def generate_order_number() -> str:
    return f"ORD-{uuid.uuid4().hex[:10].upper()}"


def generate_payment_reference() -> str:
    return f"PAY-{uuid.uuid4().hex[:12].upper()}"


def money(value) -> str:
    return f"{float(value):.2f}"
