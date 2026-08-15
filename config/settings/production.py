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

WEAK_SECRET_KEYS = {
    "unsafe-dev-key",
    "change-me-dev-only-ecommerce",
    "change-me-dev-only-ecommerce-use-50-chars-min-in-prod",
    "ci-test-secret-key-not-for-production-0123456789",
}
if (
    not SECRET_KEY
    or SECRET_KEY in WEAK_SECRET_KEYS
    or SECRET_KEY.startswith("change-me")
    or SECRET_KEY.startswith("replace-with")
):
    raise ImproperlyConfigured("Set a strong SECRET_KEY in production.")
if len(SECRET_KEY) < 40:
    raise ImproperlyConfigured("SECRET_KEY must be at least 40 characters.")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise ImproperlyConfigured("Set ALLOWED_HOSTS to your public domain(s).")
_render_host = env("RENDER_EXTERNAL_HOSTNAME", default="")
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)
if not env("DATABASE_URL", default=""):
    raise ImproperlyConfigured("DATABASE_URL is required in production.")
if not env("CHAPA_SECRET_KEY", default="") and not env("STRIPE_SECRET_KEY", default=""):
    raise ImproperlyConfigured("Set CHAPA_SECRET_KEY or STRIPE_SECRET_KEY in production.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
_render_origin = f"https://{_render_host}" if _render_host else ""
if _render_origin and _render_origin not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [_render_origin]
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
