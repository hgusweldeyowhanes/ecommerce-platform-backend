from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from common.throttles import AuthThrottle

from .models import Address
from .permissions import IsSelf
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from . import services

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [AuthThrottle]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        allowed = {"first_name", "last_name", "email", "phone"}
        for key, value in request.data.items():
            if key in allowed:
                setattr(request.user, key, value)
        request.user.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not request.user.check_password(ser.validated_data["old_password"]):
            return Response({"detail": "Wrong password", "code": "wrong_password"}, status=400)
        request.user.set_password(ser.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password updated"})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=ser.validated_data["email"]).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_mail(
                "Reset your password",
                f"Use uid={uid} and token={token} with POST /api/v1/auth/password/reset/confirm/",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        return Response({"detail": "If that email exists, a reset message was sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(ser.validated_data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, OverflowError, TypeError):
            return Response({"detail": "Invalid reset link", "code": "invalid_token"}, status=400)
        if not default_token_generator.check_token(user, ser.validated_data["token"]):
            return Response({"detail": "Invalid or expired token", "code": "invalid_token"}, status=400)
        user.set_password(ser.validated_data["password"])
        user.save()
        return Response({"detail": "Password reset complete"})


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsSelf]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        data = serializer.validated_data
        address = services.create_address(self.request.user, **data)
        serializer.instance = address
