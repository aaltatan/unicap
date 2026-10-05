from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from django.contrib.messages import get_messages
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

from .managers.base import chapters

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
