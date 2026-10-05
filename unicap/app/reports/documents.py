"""The Word / PDF documents a user downloads: the data, the (uploaded or built-in) template, filled.

A PDF is kept for an hour (`REPORTS_CACHE`): the same report asked for again is not converted again.

Imported as `from ..reports import documents` (it reads models; the package does not).
"""

import hashlib
import json
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.cache import caches
from django.utils.translation import gettext as _

from unicap.domain import ChapterReport, FacultyReport

from ..choices import ReportChoices
from ..exceptions import UserError
from ..models import Chapter, Faculty, ReportTemplate
from .audit import audit_context
from .context import (
    capacity_context,
    capacity_pivot_context,
    faculty_context,
    faculty_pivot_context,
)
from .docx import render
from .pdf import to_pdf

Context = dict[str, Any]

CHAPTER_REPORTS: dict[str, Callable[[Chapter, ChapterReport], Context]] = {
    ReportChoices.CAPACITY: capacity_context,
    ReportChoices.CAPACITY_PIVOT: capacity_pivot_context,
    ReportChoices.AUDIT: audit_context,
}

FACULTY_REPORTS: dict[str, Callable[[Chapter, Faculty, FacultyReport], Context]] = {
    ReportChoices.FACULTY_STAFF: faculty_context,
    ReportChoices.FACULTY_STAFF_PIVOT: faculty_pivot_context,
}


def chapter_context(chapter: Chapter, report: str) -> Context:
    """What a chapter's report shows (`capacity`, `capacity_pivot` or `capacity_audit`).

    Raises:
        DomainError: the chapter's data breaks a domain rule.
    """
    return CHAPTER_REPORTS[report](chapter, Chapter.objects.get_snapshot(chapter.pk).report())


def faculty_report_context(chapter: Chapter, faculty: Faculty, report: str) -> Context:
    """What a faculty's report shows (`faculty_staff` or `faculty_staff_pivot`).

    Raises:
        DomainError: the chapter's data breaks a domain rule.
        UserError: the faculty is not in the chapter.
    """
    [faculty] = Faculty.objects.attach_reports([faculty], chapter.pk)

    if faculty.report is None:  # only a faculty of another chapter has no report here
        msg = _("%(faculty)s is not in this chapter") % {"faculty": faculty.name}
        raise UserError(msg)

    return FACULTY_REPORTS[report](chapter, faculty, faculty.report)


def chapter_document(chapter: Chapter, report: str, language: str, extension: str) -> bytes:
    """A chapter's report as a .docx or .pdf file.

    Raises:
        DomainError: the chapter's data breaks a domain rule.
        ReportTemplateError: the template cannot be filled.
        PdfError: the PDF cannot be made.

    Example:
        ```python
        chapter_document(chapter, ReportChoices.CAPACITY, "ar", "pdf")
        ```
    """
    return _document(report, language, extension, chapter_context(chapter, report))


def faculty_document(
    chapter: Chapter, faculty: Faculty, report: str, language: str, extension: str
) -> bytes:
    """A faculty's report (its numbers and its own staff) as a .docx or .pdf file.

    Raises:
        DomainError: the chapter's data breaks a domain rule.
        UserError: the faculty is not in the chapter.
        ReportTemplateError: the template cannot be filled.
        PdfError: the PDF cannot be made.
    """
    context = faculty_report_context(chapter, faculty, report)

    return _document(report, language, extension, context)


def _document(report: str, language: str, extension: str, context: Context) -> bytes:
    source = ReportTemplate.objects.get_source(report, language)

    if extension != "pdf":
        return render(source, context)

    template = source.read_bytes() if isinstance(source, Path) else source.read()

    return caches[settings.REPORTS_CACHE].get_or_set(
        _pdf_key(template, context),
        lambda: to_pdf(render(BytesIO(template), context)),
    )


def _pdf_key(template: bytes, context: Context) -> str:
    """The same template filled with the same values is the same PDF: converted once.

    The values hold today's date and every number shown, so a change in the chapter (or a
    new day, or a new template) is another key.
    """
    values = json.dumps(context, sort_keys=True, default=str, ensure_ascii=False).encode()

    return f"report-pdf:{hashlib.sha256(template + values).hexdigest()}"
