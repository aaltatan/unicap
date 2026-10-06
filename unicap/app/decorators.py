from collections.abc import Callable
from functools import wraps
from typing import Concatenate, cast

from django.contrib import messages
from django.http import HttpResponse, HttpResponseBase
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from .requests import AppRequest, ChapterRequest


def chapter_required[**P, R: HttpResponseBase](
    view: Callable[Concatenate[ChapterRequest, P], R],
) -> Callable[Concatenate[AppRequest, P], R | HttpResponse]:
    """Chapter-owned pages need a chapter: without one, go create it first."""

    @wraps(view)
    def wrapper(request: AppRequest, *args: P.args, **kwargs: P.kwargs) -> R | HttpResponse:
        if request.chapter is None:
            messages.info(request, _("Create a chapter first: every page shows one chapter."))

            if request.htmx:
                response = HttpResponse("")
                response["HX-Redirect"] = "/chapters/"
                return response

            return redirect("chapters:index")

        return view(cast("ChapterRequest", request), *args, **kwargs)

    return wrapper
