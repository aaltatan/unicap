"""Settings shared by every environment. Secrets and hosts come from `.env` (python-decouple)."""

from pathlib import Path

from decouple import Csv, config
from django.utils.translation import gettext_lazy as _

# the Django root, unicap/: the `unicap` project package, `app`, `domain`, templates, static, ...
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# Application definition

CORE_APPS = [
    "unicap.app.apps.UniCapAdminConfig",  # django.contrib.admin, superusers only
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "django_cotton",
    "django_filters",
    "django_htmx",
    "djangoql",
    "heroicons",
    "import_export",
    "widget_tweaks",
    "django_vite",
    "corsheaders",
    "django_cleanup",
    "solo",
    "rest_framework",
    "rest_framework_simplejwt",
]

LOCAL_APPS = [
    "unicap.app",
]

INSTALLED_APPS = CORE_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "unicap.app.middlewares.CurrentChapterMiddleware",
    "unicap.app.middlewares.HtmxMessagesMiddleware",
    "unicap.app.middlewares.DomainErrorMiddleware",
]

ROOT_URLCONF = "unicap.unicap.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "unicap.unicap.constants.constants",
            ],
            "builtins": [
                "heroicons.templatetags.heroicons",
                "unicap.app.templatetags.utils",
            ],
        },
    },
]

WSGI_APPLICATION = "unicap.unicap.wsgi.application"

# Database: MySQL by default, or a local SQLite file when DB_ENGINE names sqlite3

DB_ENGINE = config("DB_ENGINE", default="django.db.backends.mysql")

if DB_ENGINE.endswith("sqlite3"):
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": BASE_DIR / config("DB_NAME", default="db.sqlite3"),
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="3306"),
            "OPTIONS": {"sql_mode": "traditional", "charset": "utf8mb4"},
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization, English and Arabic (right to left)

LANGUAGE_CODE = "en"

LANGUAGES = (
    ("en", _("English")),
    ("ar", _("Arabic")),
)

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = config("TIME_ZONE", default="Asia/Damascus")

USE_I18N = True

USE_TZ = True

# Static & media

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# files no URL serves (the backups): never inside MEDIA_ROOT or a folder the web server serves
PRIVATE_MEDIA_ROOT = Path(config("PRIVATE_MEDIA_ROOT", default=str(BASE_DIR / "private")))

# LibreOffice's `soffice`, converting the Word reports to PDF (empty: found on the PATH)
SOFFICE_PATH = config("SOFFICE_PATH", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Authentication

AUTH_USER_MODEL = "app.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"

# Cotton

COTTON_DIR = "components"
COTTON_SNAKE_CASED_NAMES = False

# Cache (django-solo reads its singletons through it)

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "local": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    # converted PDF reports: converting takes seconds, the same report is asked for again
    "reports": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "reports",
        "TIMEOUT": 60 * 60,
        "OPTIONS": {"MAX_ENTRIES": 50},
    },
}

SOLO_CACHE = "local"
REPORTS_CACHE = "reports"

# CORS

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

# REST API (/api/): a logged-in session, or a JWT from /api/token/

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

# Vite: `npm run dev` serves the assets when dev_mode is on, otherwise `npm run build`
# writes them, with their manifest, to static/dist/ (keep in sync with vite.config.mjs)

DJANGO_VITE = {
    "default": {
        "dev_mode": config("VITE_DEV_MODE", default=DEBUG, cast=bool),
        "static_url_prefix": "dist",
        "manifest_path": BASE_DIR / "static" / "dist" / "manifest.json",
    },
}

# Import / export

IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = True
