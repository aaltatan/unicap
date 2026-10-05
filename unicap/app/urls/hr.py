from django.urls import URLPattern, URLResolver, include, path

patterns: list[URLPattern | URLResolver] = [
    path("employees/", include("unicap.app.urls.employees")),
    path("contracts/", include("unicap.app.urls.contracts")),
]
