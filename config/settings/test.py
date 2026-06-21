"""Test settings: fast, in-memory channel layer, local sqlite-free Postgres or sqlite."""
from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False

# Allow running tests without Postgres by falling back to sqlite.
if config("TEST_USE_SQLITE", default=True, cast=bool):
    DATABASES["default"] = {  # noqa: F405
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Keep media out of the repo during tests.
MEDIA_ROOT = BASE_DIR / "test_media"  # noqa: F405
