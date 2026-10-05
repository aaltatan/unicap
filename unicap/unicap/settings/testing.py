import logging
import os

os.environ.setdefault("SECRET_KEY", "testing-only-secret-key")

from unicap.unicap.settings.base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DJANGO_VITE = {"default": {"dev_mode": True}}

logging.disable()
