from django.urls import path

from ..views import backups as views

app_name = "backups"

urlpatterns = [
    path(route="", view=views.index, name="index"),
    path(route="create/", view=views.create, name="create"),
    path(route="upload/", view=views.upload, name="upload"),
    path(route="<int:pk>/download/", view=views.download, name="download"),
    path(route="<int:pk>/restore/", view=views.restore, name="restore"),
    path(route="<int:pk>/delete/", view=views.delete, name="delete"),
]
