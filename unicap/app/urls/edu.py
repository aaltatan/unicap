from django.urls import URLPattern, URLResolver, include, path

patterns: list[URLPattern | URLResolver] = [
    path("specializations/", include("unicap.app.urls.specializations")),
    path("faculties/", include("unicap.app.urls.faculties")),
]
