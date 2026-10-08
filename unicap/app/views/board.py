"""The drag-and-drop board: one lane per faculty plus the unsigned lane.

Cards are green when the ministry counts the contract, red when it does not, grey while
unsigned, faded when left out of the calculation. Every number comes from evaluating
the chapter with the domain.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from unicap.domain import DomainError, Strategy

from .. import forms
from ..choices import RECOMMENDATION_STRATEGY_DESCRIPTIONS, STRATEGY_DESCRIPTIONS, StrategyChoices
from ..decorators import chapter_required
from ..exceptions import UserError
from ..models import AppSettings, Chapter, Contract
from ..requests import ChapterRequest
from ..snapshot import Optimization
from ..templatetags.domain import status_label
from ..texts import error_text
from .crud import trigger

BOARD_TARGET = "board"


@require_GET
@permission_required("app.view_contract", raise_exception=True)
@chapter_required
def index(request: ChapterRequest) -> HttpResponse:
    template = (
        "components/board/board.html"
        if request.htmx and request.htmx.target == BOARD_TARGET
        else "app/board/index.html"
    )

    return render(request, template, _board_context(request))


@require_POST
@permission_required("app.change_contract", raise_exception=True)
@chapter_required
def move(request: ChapterRequest) -> HttpResponse:
    """A card was dropped: sign its contract to the lane's faculty (none: unsigned)."""
    contract = _contract_of(request, request.POST.get("employee"))

    faculty_id = request.POST.get("faculty") or None

    try:
        Contract.objects.move(contract, int(faculty_id) if faculty_id else None)
    except (DomainError, UserError, ValueError) as error:
        messages.error(request, error_text(error))

    return _board(request)


@require_GET
@permission_required("app.view_contract", raise_exception=True)
@chapter_required
def preview(request: ChapterRequest) -> JsonResponse:
    """While dragging: per lane, the status the card would get and the capacity after."""
    contract = _contract_of(request, request.GET.get("employee"))

    snapshot = Chapter.objects.get_snapshot(request.chapter.pk)

    name = contract.employee.name

    lanes = {}

    for drop in snapshot.drop_previews(contract.employee_id):
        key = "unsigned" if drop.faculty_id is None else str(drop.faculty_id)

        place = _("unsigned") if drop.faculty_id is None else snapshot.numbers(drop.faculty_id).name

        lanes[key] = {
            "counted": None if drop.status is None else drop.status.is_counted,
            "status": status_label(drop.status),
            "capacity": drop.capacity,
            "hint": _("%(name)s on %(place)s: %(status)s · capacity would be %(capacity)s")
            % {
                "name": name,
                "place": place,
                "status": status_label(drop.status),
                "capacity": drop.capacity,
            },
        }

    return JsonResponse({"lanes": lanes})


@require_POST
@permission_required("app.change_contract", raise_exception=True)
@chapter_required
def toggle(request: ChapterRequest) -> HttpResponse:
    """A card's menu: switch one of its contract's two-valued terms (default: on / off)."""
    contract = _contract_of(request, request.POST.get("employee"))

    try:
        Contract.objects.switch(contract, request.POST.get("field", "is_active"))
    except (DomainError, UserError) as error:
        messages.error(request, error_text(error))

    return _board(request)


@require_http_methods(["GET", "POST"])
@permission_required("app.change_contract", raise_exception=True)
@chapter_required
def reset(request: ChapterRequest) -> HttpResponse:
    """Make every contract of the chapter unsigned (after a confirmation)."""
    chapter = request.chapter

    if request.method == "POST":
        count = Chapter.objects.reset(chapter)
        messages.success(request, _("%(count)s contract(s) are unsigned now.") % {"count": count})
        return trigger(HttpResponse(""), refresh=True, **{"close-modal": True})

    signed = Contract.objects.for_chapter(chapter.pk).signed()

    context = {
        "signed": signed.movable().count(),
        "locked": signed.pinned().count(),
        "chapter": chapter,
    }

    return render(request, "app/board/reset-modal.html", context)


@require_http_methods(["GET", "POST"])
@permission_required("app.change_contract", raise_exception=True)
@chapter_required
def optimize(request: ChapterRequest) -> HttpResponse:
    """GET: preview a strategy's placement next to the current one. POST: trim or apply it.

    A move's select names the employee who makes it: the optimizer's, or one just like them.
    Its button removes it (`remove`) or puts it back (`restore`): the preview is drawn again
    with the figures of the moves kept. Any other POST applies the moves kept.
    """
    if request.method == "GET":
        strategy = _strategy(request.GET.get("strategy"))

        snapshot = Chapter.objects.get_snapshot(request.chapter.pk)

        optimization = snapshot.optimization(strategy, AppSettings.get_solo().optimizer_rounds)

        return _optimization(request, optimization)

    placements = _placements(request.POST.get("placements", "{}"))
    substitutes = _substitutes(request.POST)
    removed = _removed(request.POST)

    if "remove" in request.POST or "restore" in request.POST:
        snapshot = Chapter.objects.get_snapshot(request.chapter.pk)
        strategy = _strategy(request.POST.get("strategy"))

        try:
            optimization = snapshot.review(
                strategy, placements, removed=removed, substitutes=substitutes
            )
        except UserError as error:  # a substitute chosen twice: drawn again without them
            messages.error(request, error_text(error))
            optimization = snapshot.review(strategy, placements, removed=removed)

        return _optimization(request, optimization, focused=_changed_move(request.POST))

    try:
        moved = Chapter.objects.apply_placements(
            request.chapter, placements, substitutes=substitutes, removed=removed
        )
    except (DomainError, UserError) as error:
        messages.error(request, error_text(error))
    else:
        messages.success(request, _("%(count)s contract(s) re-signed.") % {"count": moved})

    return trigger(HttpResponse(""), refresh=True, **{"close-modal": True})


@require_GET
@permission_required("app.view_contract", raise_exception=True)
@chapter_required
def recommend(request: ChapterRequest) -> HttpResponse:
    """The contracts to sign to solve the chapter's problems, for a strategy. Nothing is saved."""
    form = forms.RecommendationForm(request.GET if "strategy" in request.GET else None)

    context: dict[str, object] = {"form": form}

    if form.is_valid():
        snapshot = Chapter.objects.get_snapshot(request.chapter.pk)

        strategy = form.strategy_value()

        context |= {
            "recommendation": snapshot.recommendation(
                strategy,
                kinds=form.kinds_value(),
                optimize_first=form.cleaned_data["optimize_first"],
                max_rounds=AppSettings.get_solo().optimizer_rounds,
            ),
            "strategy_description": RECOMMENDATION_STRATEGY_DESCRIPTIONS[strategy],
        }

    return render(request, "app/board/recommend-modal.html", context)


def _optimization(
    request: ChapterRequest, optimization: Optimization, *, focused: int | None = None
) -> HttpResponse:
    """The optimizer's modal; `focused`: the move whose button was just pressed."""
    strategy = optimization.strategy

    context = {
        "optimization": optimization,
        "strategy": strategy.value,
        "strategy_label": StrategyChoices(strategy.value).label,
        "strategy_description": STRATEGY_DESCRIPTIONS[strategy],
        "placements": json.dumps({str(k): v for k, v in optimization.placements.items()}),
        "focused": focused,
    }

    return render(request, "app/board/optimize-modal.html", context)


def _board(request: ChapterRequest) -> HttpResponse:
    return render(request, "components/board/board.html", _board_context(request))


def _board_context(request: ChapterRequest) -> dict[str, object]:
    snapshot = Chapter.objects.get_snapshot(request.chapter.pk)

    report = snapshot.report()

    return {
        "page_title": _("board"),
        "report": report,
        "lanes": snapshot.lanes(report),
        "strategies": StrategyChoices.choices,
        "strategy_descriptions": {s.value: str(d) for s, d in STRATEGY_DESCRIPTIONS.items()},
        "can_move": request.user.has_perm("app.change_contract"),
        "can_edit_faculties": request.user.has_perm("app.change_faculty"),
    }


def _contract_of(request: ChapterRequest, employee_id: str | None) -> Contract:
    return get_object_or_404(
        Contract.objects.for_chapter(request.chapter.pk).select_related("employee"),
        employee_id=employee_id if (employee_id or "").isdigit() else 0,
    )


def _strategy(value: str | None) -> Strategy:
    """The strategy the select sent; anything else is the default one."""
    return Strategy(value) if value in StrategyChoices.values else Strategy.MAXIMIZE_STUDENTS


def _removed(data: QueryDict) -> set[int]:
    """The moves taken out: those marked `removed`, plus `remove`, minus `restore`."""
    removed = {int(value) for value in data.getlist("removed") if value.isdigit()}

    if (remove := data.get("remove", "")).isdigit():
        removed.add(int(remove))

    if (restore := data.get("restore", "")).isdigit():
        removed.discard(int(restore))

    return removed


def _changed_move(data: QueryDict) -> int | None:
    """The move whose remove / restore button was pressed."""
    value = data.get("remove") or data.get("restore") or ""

    return int(value) if value.isdigit() else None


def _substitutes(data: QueryDict) -> dict[int, int]:
    """`substitute-12=15` (a moved contract's id = the contract moved instead) from the form."""
    prefix = "substitute-"

    return {
        int(name.removeprefix(prefix)): int(value)
        for name in data
        if name.startswith(prefix)
        and name.removeprefix(prefix).isdigit()
        and (value := data.get(name, "")).isdigit()
    }


def _placements(value: str) -> dict[int, int | None]:
    """`{"12": 3, "13": null}` (contract id -> faculty id) from the preview's form.

    Anything else (not JSON, not an object, ids that are not numbers) places nothing.
    """
    try:
        raw = json.loads(value)
    except json.JSONDecodeError:
        return {}

    if not isinstance(raw, dict):
        return {}

    try:
        return {
            int(contract): (int(faculty) if faculty is not None else None)
            for contract, faculty in raw.items()
        }
    except (TypeError, ValueError):
        return {}
