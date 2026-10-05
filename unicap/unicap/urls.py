from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

from unicap.app.urls import patterns as app_patterns

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include(app_patterns)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if "silk" in settings.INSTALLED_APPS:  # development only: the SQL profiler
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
