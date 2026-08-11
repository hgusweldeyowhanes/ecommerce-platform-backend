from django.contrib.auth import get_user_model

from .models import Address

User = get_user_model()


def get_user_by_id(user_id):
    return User.objects.filter(pk=user_id).first()


def list_addresses(user):
    return Address.objects.filter(user=user)
