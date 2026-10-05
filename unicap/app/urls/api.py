from django.contrib.auth.decorators import login_not_required
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from ..views import api

app_name = "api"

urlpatterns = [
    path(route="capacity/calculate/", view=api.calculate, name="calculate"),
    path(
        route="token/",
        view=login_not_required(TokenObtainPairView.as_view()),
        name="token",
    ),
    path(
        route="token/refresh/",
        view=login_not_required(TokenRefreshView.as_view()),
        name="token-refresh",
    ),
]
