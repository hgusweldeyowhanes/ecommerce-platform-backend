from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
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
from .tokens import email_verify_token, send_email_verification, send_password_reset

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
            send_password_reset(user)
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


class EmailVerifyRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        if request.user.email_verified:
            return Response({"detail": "Already verified"})
        if not request.user.email:
            return Response({"detail": "Add an email first"}, status=400)
        send_email_verification(request.user)
        return Response({"detail": "Verification email sent"})


class EmailVerifyConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        uid = request.data.get("uid") or ""
        token = request.data.get("token") or ""
        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, OverflowError, TypeError):
            return Response({"detail": "Invalid link", "code": "invalid_token"}, status=400)
        if not email_verify_token.check_token(user, token):
            return Response({"detail": "Invalid or expired token", "code": "invalid_token"}, status=400)
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        return Response({"detail": "Email verified"})


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsSelf]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        data = serializer.validated_data
        address = services.create_address(self.request.user, **data)
        serializer.instance = address
