from unicap.unicap.settings.base import *

DEBUG = True

INTERNAL_IPS = ["127.0.0.1"]

# django-silk at /silk/: every request's SQL queries, their duplicates and their time
INSTALLED_APPS = [*INSTALLED_APPS, "silk"]

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
