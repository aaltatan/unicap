from django.urls import path

from ..views import contracts as views

app_name = "contracts"

urlpatterns = [
    path(route="", view=views.index, name="index"),
    path(route="create/", view=views.create, name="create"),
    path(route="import/", view=views.import_file, name="import"),
    path(route="bulk-delete/", view=views.bulk_delete, name="bulk-delete"),
    path(route="bulk-edit/", view=views.bulk_edit, name="bulk-edit"),
    path(route="bulk-action/", view=views.bulk_action, name="bulk-action"),
    path(route="<int:pk>/", view=views.details, name="details"),
    path(route="<int:pk>/update/", view=views.update, name="update"),
    path(route="<int:pk>/delete/", view=views.delete, name="delete"),
    path(route="<int:pk>/toggle/", view=views.toggle, name="toggle"),
]
