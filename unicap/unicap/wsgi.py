import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unicap.unicap.settings.deployment")

application = get_wsgi_application()
