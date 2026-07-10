"""Production (local on-premise server) settings."""
from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost", cast=Csv())

# Security hardening for the local production server. HTTPS is optional on a
# trusted LAN, so cookie-secure flags default to False and can be enabled.
SESSION_COOKIE_SECURE = config("DJANGO_SECURE_COOKIES", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("DJANGO_SECURE_COOKIES", default=False, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

# Behind a TLS-terminating proxy (Cloudflare Tunnel → nginx). nginx forwards the
# original scheme in X-Forwarded-Proto so Django knows the request was HTTPS;
# this makes request.is_secure() / secure cookies / CSRF https checks correct.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Serve static files behind Nginx; collected into STATIC_ROOT.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    },
}

SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=False, cast=bool)
