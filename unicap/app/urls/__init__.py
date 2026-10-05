from django.urls import URLPattern, URLResolver, include, path

from ..views import search
from .edu import patterns as edu_patterns
from .hr import patterns as hr_patterns

patterns: list[URLPattern | URLResolver] = [
    path("", include("unicap.app.urls.board")),
    path("chapters/", include("unicap.app.urls.chapters")),
    path("reports/", include("unicap.app.urls.reports")),
    path("backups/", include("unicap.app.urls.backups")),
    path("api/", include("unicap.app.urls.api")),
    path("search/", search.index, name="search"),
    path("edu/", include((edu_patterns, "edu"))),
    path("hr/", include((hr_patterns, "hr"))),
]
