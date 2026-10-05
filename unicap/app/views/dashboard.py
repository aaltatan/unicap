"""The dashboard: the chapter at a glance (the reports' pages read the same numbers)."""

from typing import cast

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from unicap.domain import DomainError

from ..models import Chapter
from ..requests import AppRequest, ChapterRequest
from ..texts import error_text


@require_GET
@login_required
def dashboard(request: AppRequest) -> HttpResponse:
    if request.chapter is None:
        return render(request, "app/board/welcome.html", {"page_title": _("welcome")})

    context = report_context(cast("ChapterRequest", request), _("dashboard"))

    return render(request, "app/board/dashboard.html", context)


def report_context(request: ChapterRequest, title: str) -> dict[str, object]:
    chapter = request.chapter

    try:
        snapshot = Chapter.objects.get_snapshot(chapter.pk)
    except DomainError as error:
        return {"page_title": title, "chapter": chapter, "problem": error_text(error)}

    chapter_report = snapshot.report()

    return {
        "page_title": title,
        "chapter": chapter,
        "report": chapter_report,
        "lanes": snapshot.lanes(chapter_report)[1:],
        "counts": snapshot.status_counts(chapter_report),
        "contracts": len(snapshot.chapter.contracts),
    }
