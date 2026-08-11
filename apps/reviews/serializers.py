from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "product",
            "user",
            "username",
            "rating",
            "title",
            "body",
            "is_approved",
            "created_at",
        )
        read_only_fields = ("user", "is_approved", "created_at")
