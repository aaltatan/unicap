"""Production (PythonAnywhere, or any host behind an HTTPS proxy): `.env` holds the rest."""

from unicap.unicap.settings.base import *

DEBUG = False

# HTTPS: the proxy in front ends it and says so in this header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30, cast=int)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

# the built assets (`npm run build`, kept in the repository), whatever DEBUG says in `.env`
DJANGO_VITE = {"default": {**DJANGO_VITE["default"], "dev_mode": False}}

# warnings and errors to stderr: the host keeps it as the site's error log
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
