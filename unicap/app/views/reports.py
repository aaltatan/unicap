"""The reports: each a page to read or print, and a Word / PDF file from its template.

  capacity          the chapter's head counts and capacity per faculty (and its pivot)
  audit             how every capacity is calculated, step by step
  faculties         each faculty's own staff (and its pivot)

A file is the report's (admin-editable) Word template, filled; admins download the built-in
templates as the starting point of their own.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from unicap.domain import DomainError

from ..choices import ReportChoices
from ..decorators import chapter_required
from ..exceptions import UserError
from ..models import Faculty
from ..querysets.base import BaseQuerySet
from ..reports import attachment, default_path, documents
from ..reports.docx import DOCX_CONTENT_TYPE
from ..requests import AppRequest, ChapterRequest
from ..texts import error_text
from .dashboard import report_context

# each report's page: its url name (its files are `<name>-docx`, `<name>-pdf`) and template
CHAPTER_PAGES = {
    ReportChoices.CAPACITY: ("reports:capacity", "app/reports/capacity.html"),
    ReportChoices.CAPACITY_PIVOT: ("reports:capacity-pivot", "app/reports/capacity-pivot.html"),
    ReportChoices.AUDIT: ("reports:audit", "app/reports/audit.html"),
}

FACULTY_PAGES = {
    ReportChoices.FACULTY_STAFF: ("reports:staff", "app/reports/staff.html"),
    ReportChoices.FACULTY_STAFF_PIVOT: ("reports:staff-pivot", "app/reports/staff-pivot.html"),
}


@require_GET
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def capacity(request: ChapterRequest) -> HttpResponse:
    """The capacity report: the seven head counts and the capacity of every faculty."""
    _name, template = CHAPTER_PAGES[ReportChoices.CAPACITY]

    return render(request, template, report_context(request, _("capacity report")))


@require_GET
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def chapter_page(request: ChapterRequest, report: str) -> HttpResponse:
    """A chapter's report drawn from its document's values (the pivot, the audit)."""
    _name, template = CHAPTER_PAGES[report]

    context: dict[str, object] = {
        "page_title": ReportChoices(report).label,
        "chapter": request.chapter,
    }

    try:
        context.update(documents.chapter_context(request.chapter, report))
    except DomainError as error:
        context["problem"] = error_text(error)

    return render(request, template, context)


@require_GET
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def chapter_file(request: ChapterRequest, report: str, extension: str) -> HttpResponseBase:
    """A chapter's report as a Word or PDF file, from its (admin-editable) template."""
    try:
        content = documents.chapter_document(request.chapter, report, get_language(), extension)
    except (DomainError, UserError) as error:
        messages.error(request, error_text(error))
        return redirect(CHAPTER_PAGES[report][0])

    title = str(ReportChoices(report).label)

    return attachment(content, title, request.chapter.name, extension=extension)


@require_GET
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def faculties(request: ChapterRequest) -> HttpResponse:
    """Every faculty of the chapter, with its own reports."""
    chapter_id = request.chapter.pk

    context: dict[str, object] = {"page_title": _("faculty reports"), "chapter": request.chapter}

    try:
        context["faculties"] = Faculty.objects.attach_reports(
            Faculty.objects.for_chapter(chapter_id), chapter_id
        )
    except DomainError as error:
        context["problem"] = error_text(error)

    return render(request, "app/reports/faculties.html", context)


@require_GET
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def staff(request: ChapterRequest, pk: int) -> HttpResponse:
    """A printable page for the faculty: its numbers and its own staff."""
    faculty = _faculty(request, pk, Faculty.objects.with_shares())

    [faculty] = Faculty.objects.attach_reports([faculty], request.chapter.pk)

    _name, template = FACULTY_PAGES[ReportChoices.FACULTY_STAFF]

    return render(
        request,
        template,
        {"page_title": faculty.name, "chapter": request.chapter, "obj": faculty},
    )


@require_GET
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def faculty_page(request: ChapterRequest, pk: int, report: str) -> HttpResponse:
    """A faculty's report drawn from its document's values (the staff pivot)."""
    faculty = _faculty(request, pk)

    _name, template = FACULTY_PAGES[report]

    context: dict[str, object] = {
        "page_title": faculty.name,
        "chapter": request.chapter,
        "obj": faculty,
    }

    try:
        context.update(documents.faculty_report_context(request.chapter, faculty, report))
    except (DomainError, UserError) as error:
        context["problem"] = error_text(error)

    return render(request, template, context)


@require_GET
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def faculty_file(request: ChapterRequest, pk: int, report: str, extension: str) -> HttpResponseBase:
    """A faculty's report as a Word or PDF file, from its (admin-editable) template."""
    faculty = _faculty(request, pk)

    try:
        content = documents.faculty_document(
            request.chapter, faculty, report, get_language(), extension
        )
    except (DomainError, UserError) as error:
        messages.error(request, error_text(error))
        return redirect(FACULTY_PAGES[report][0], pk=faculty.pk)

    return attachment(content, faculty.name, request.chapter.name, extension=extension)


@require_GET
@permission_required("app.change_reporttemplate", raise_exception=True)
def default_template(request: AppRequest, report: str, language: str) -> FileResponse:  # noqa: ARG001
    """A built-in Word template, the starting point of an admin's own."""
    if report not in ReportChoices.values or language not in dict(settings.LANGUAGES):
        raise Http404

    path = default_path(report, language)

    return FileResponse(
        path.open("rb"),
        as_attachment=True,
        filename=path.name,
        content_type=DOCX_CONTENT_TYPE,
    )


def _faculty(request: ChapterRequest, pk: int, queryset: BaseQuerySet | None = None) -> Faculty:
    rows = queryset if queryset is not None else Faculty.objects.all()

    return get_object_or_404(rows.for_chapter(request.chapter.pk), pk=pk)
