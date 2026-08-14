"""Production settings. Fails fast if secrets or hosts are missing."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False
CELERY_TASK_ALWAYS_EAGER = False
ALLOW_MOCK_PAYMENTS = False
USE_REDIS_CACHE = True
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "ecom",
        "TIMEOUT": 300,
    }
}

if not SECRET_KEY or SECRET_KEY in {"unsafe-dev-key", "change-me-dev-only-ecommerce"}:
    raise ImproperlyConfigured("Set a strong SECRET_KEY in production.")
if len(SECRET_KEY) < 40:
    raise ImproperlyConfigured("SECRET_KEY must be at least 40 characters.")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS to your public domain(s).")
if not env("DATABASE_URL", default=""):
    raise ImproperlyConfigured("DATABASE_URL is required in production.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOW_ALL_ORIGINS = False

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
