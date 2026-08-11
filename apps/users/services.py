from django.db import transaction

from .models import Address


@transaction.atomic
def set_default_address(user, address: Address) -> Address:
    Address.objects.filter(user=user, is_default=True).update(is_default=False)
    address.is_default = True
    address.save(update_fields=["is_default"])
    return address


def create_address(user, **data) -> Address:
    if data.get("is_default"):
        Address.objects.filter(user=user, is_default=True).update(is_default=False)
    return Address.objects.create(user=user, **data)
