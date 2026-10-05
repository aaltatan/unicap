"""The header's search: every kind of row at once."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from ..requests import AppRequest
from ..search import search_everything


@require_GET
@login_required
def index(request: AppRequest) -> HttpResponse:
    value = request.GET.get("q", "")

    groups = search_everything(request.user, getattr(request, "chapter", None), value)

    return render(request, "app/search/results.html", {"q": value.strip(), "groups": groups})
