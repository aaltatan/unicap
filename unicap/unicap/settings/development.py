"""Development: `manage.py`'s default settings, with the development tools when they are there."""

from importlib.util import find_spec

from unicap.unicap.settings.base import *

DEBUG = True

INTERNAL_IPS = ["127.0.0.1"]

# The development tools (the `dev` dependency group), each only when it is installed: a server
# holds the production requirements alone, and `manage.py` there (these settings, unless
# DJANGO_SETTINGS_MODULE names the deployment ones) must not fail on a missing package.
#   django_extensions  shell_plus, show_urls, ...
#   silk               /silk/: every request's SQL queries, their duplicates and their time
DEV_APPS = [app for app in ("django_extensions", "silk") if find_spec(app)]

INSTALLED_APPS = [*INSTALLED_APPS, *DEV_APPS]

if "silk" in DEV_APPS:
    MIDDLEWARE = [
        *MIDDLEWARE[: MIDDLEWARE.index("django_htmx.middleware.HtmxMiddleware")],
        "silk.middleware.SilkyMiddleware",
        *MIDDLEWARE[MIDDLEWARE.index("django_htmx.middleware.HtmxMiddleware") :],
    ]

SILKY_AUTHENTICATION = True  # only a logged-in ...
SILKY_AUTHORISATION = True  # ... superuser reads the profiles
SILKY_PERMISSIONS = lambda user: user.is_superuser  # noqa: E731 - silk's own setting shape
SILKY_MAX_RECORDED_REQUESTS = 2000  # the oldest are dropped: the table stays small
SILKY_MAX_RESPONSE_BODY_SIZE = 0  # the pages themselves are not kept, only their queries
SILKY_META = True  # what profiling itself cost each request
