from django.urls import path

from ..views import chapters as views

app_name = "chapters"

urlpatterns = [
    path(route="", view=views.index, name="index"),
    path(route="create/", view=views.create, name="create"),
    path(route="select/", view=views.select, name="select"),
    path(route="bulk-delete/", view=views.bulk_delete, name="bulk-delete"),
    path(route="bulk-edit/", view=views.bulk_edit, name="bulk-edit"),
    path(route="bulk-action/", view=views.bulk_action, name="bulk-action"),
    path(route="<int:pk>/", view=views.details, name="details"),
    path(route="<int:pk>/update/", view=views.update, name="update"),
    path(route="<int:pk>/delete/", view=views.delete, name="delete"),
    path(route="<int:pk>/default/", view=views.set_default, name="set-default"),
    path(route="<int:pk>/duplicate/", view=views.duplicate, name="duplicate"),
]
