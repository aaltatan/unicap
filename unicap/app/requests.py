"""Requests as the app's middlewares leave them: for type checkers only.

`CurrentChapterMiddleware` sets `request.chapter` and django-htmx sets `request.htmx`;
`HttpRequest` knows neither. Views annotate `request: AppRequest`, and views behind
`@chapter_required` `request: ChapterRequest` (their chapter is never None).
"""

from typing import TYPE_CHECKING

from django.http import HttpRequest

if TYPE_CHECKING:
    from django_htmx.middleware import HtmxDetails

    from .models import Chapter, User


class AppRequest(HttpRequest):
    """Any request of the app: its chapter may be None (no chapter yet)."""

    chapter: "Chapter | None"
    htmx: "HtmxDetails"
    user: "User"  # LoginRequiredMiddleware: every app page has one (login page and API excepted)


class ChapterRequest(AppRequest):
    """A request of a chapter-owned page (`@chapter_required`): it has a chapter."""

    chapter: "Chapter"
