from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerifyTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.email}{user.email_verified}"


email_verify_token = EmailVerifyTokenGenerator()


def frontend_url():
    from django.conf import settings

    return getattr(settings, "FRONTEND_URL", "http://127.0.0.1:5173").rstrip("/")


def send_password_reset(user):
    from django.conf import settings
    from django.contrib.auth.tokens import default_token_generator
    from django.core.mail import send_mail
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{frontend_url()}/reset-password?uid={uid}&token={token}"
    send_mail(
        "Reset your Tradiva password",
        f"Reset your password:\n{link}\n\nIf you did not ask for this, ignore the email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


def send_email_verification(user):
    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verify_token.make_token(user)
    link = f"{frontend_url()}/verify-email?uid={uid}&token={token}"
    send_mail(
        "Verify your Tradiva email",
        f"Confirm your email:\n{link}",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )
