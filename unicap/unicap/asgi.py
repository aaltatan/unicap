import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unicap.unicap.settings.deployment")

application = get_asgi_application()
