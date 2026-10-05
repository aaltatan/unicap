"""`/reports/`: each report's page, then its files at `<page>docx/` and `<page>pdf/`.

capacity/            capacity/pivot/          audit/
faculties/           faculties/<pk>/staff/    faculties/<pk>/staff/pivot/
"""

from collections.abc import Callable
from typing import Any

from django.urls import URLPattern, path

from ..choices import ReportChoices
from ..views import reports as views

app_name = "reports"

EXTENSIONS = ("docx", "pdf")


def _files(route: str, view: Callable[..., Any], name: str, report: str) -> list[URLPattern]:
    """A report's files, beside its page: `<route>docx/` as `<name>-docx`, and its pdf."""
    return [
        path(
            route=f"{route}{extension}/",
            view=view,
            name=f"{name}-{extension}",
            kwargs={"report": report, "extension": extension},
        )
        for extension in EXTENSIONS
    ]


urlpatterns = [
    path(route="capacity/", view=views.capacity, name="capacity"),
    *_files("capacity/", views.chapter_file, "capacity", ReportChoices.CAPACITY),
    path(
        route="capacity/pivot/",
        view=views.chapter_page,
        name="capacity-pivot",
        kwargs={"report": ReportChoices.CAPACITY_PIVOT},
    ),
    *_files("capacity/pivot/", views.chapter_file, "capacity-pivot", ReportChoices.CAPACITY_PIVOT),
    path(
        route="audit/",
        view=views.chapter_page,
        name="audit",
        kwargs={"report": ReportChoices.AUDIT},
    ),
    *_files("audit/", views.chapter_file, "audit", ReportChoices.AUDIT),
    path(route="faculties/", view=views.faculties, name="faculties"),
    path(route="faculties/<int:pk>/staff/", view=views.staff, name="staff"),
    *_files("faculties/<int:pk>/staff/", views.faculty_file, "staff", ReportChoices.FACULTY_STAFF),
    path(
        route="faculties/<int:pk>/staff/pivot/",
        view=views.faculty_page,
        name="staff-pivot",
        kwargs={"report": ReportChoices.FACULTY_STAFF_PIVOT},
    ),
    *_files(
        "faculties/<int:pk>/staff/pivot/",
        views.faculty_file,
        "staff-pivot",
        ReportChoices.FACULTY_STAFF_PIVOT,
    ),
    path(
        route="templates/<str:report>/<str:language>/default/",
        view=views.default_template,
        name="default-template",
    ),
]
