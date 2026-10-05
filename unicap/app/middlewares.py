from collections.abc import Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

from django.contrib import messages
from django.contrib.messages import get_messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from unicap.domain import DomainError

from .managers.base import chapters
from .texts import error_text

if TYPE_CHECKING:
    from .models import Chapter
    from .requests import AppRequest

SESSION_CHAPTER = "chapter_id"

GetResponse = Callable[[HttpRequest], HttpResponse]


class CurrentChapterMiddleware:
    """`request.chapter`: the chapter every page shows (chosen in the header).

    The session remembers the choice; without one (or when it was deleted) it is the
    default chapter. None when there is no chapter at all.
    """

    def __init__(self, get_response: GetResponse) -> None:  # noqa: D107
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:  # noqa: D102
        cast("AppRequest", request).chapter = _current_chapter(request)

        return self.get_response(request)


class HtmxMessagesMiddleware:
    """Show queued messages after an HTMX request, as an out-of-band swap into the toasts.

    Full pages render them in the layout; redirects keep them for the next page.
    """

    def __init__(self, get_response: GetResponse) -> None:  # noqa: D107
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:  # noqa: D102
        response = self.get_response(request)

        if not _takes_messages(request, response):
            return response

        storage = get_messages(request)

        queued = list(storage)

        if queued:
            response.write(
                render_to_string(
                    "components/layout/messages-oob.html",
                    {"messages": queued},
                    request=request,
                ),
            )

        return response


class DomainErrorMiddleware:
    """A page of a chapter whose stored rows break a rule shows the rule, not a server error.

    Writes are validated before they commit, so this is rare (rows restored or edited
    behind the rules, a rule added later). The whole page becomes the problem's page (409);
    an HTMX request leaves the page as it is and shows the problem as a toast.
    """

    def __init__(self, get_response: GetResponse) -> None:  # noqa: D107
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:  # noqa: D102
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        """Answer a `DomainError` no view caught; any other exception is left alone."""
        if not isinstance(exception, DomainError):
            return None

        problem = error_text(exception)

        if getattr(request, "htmx", False):
            messages.error(request, problem)
            response = HttpResponse("")
            response["HX-Reswap"] = "none"
            return response

        context = {"page_title": _("a broken rule"), "problem": problem}

        return render(request, "app/board/problem.html", context, status=HTTPStatus.CONFLICT)


def _current_chapter(request: HttpRequest) -> "Chapter | None":
    chapter_id = request.session.get(SESSION_CHAPTER)

    chapter = chapters().filter(pk=chapter_id).first() if chapter_id else None

    return chapter or chapters().get_default()


def _takes_messages(request: HttpRequest, response: HttpResponse) -> bool:
    if not getattr(request, "htmx", False) or response.streaming:
        return False

    if any(header in response for header in ("HX-Redirect", "HX-Refresh", "HX-Location")):
        return False

    return response.status_code == 200 and response.get("Content-Type", "").startswith(  # noqa: PLR2004
        "text/html",
    )
