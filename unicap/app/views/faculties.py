from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from .. import filters, forms, resources
from ..constants import faculty as constants
from ..decorators import chapter_required
from ..models import Faculty, FacultySettings
from ..querysets.base import BaseQuerySet
from ..requests import AppRequest, ChapterRequest
from . import crud

RESOURCE = crud.Resource(
    bulk_fields=(
        "students_per_phd",
        "min_staff_percentage",
        "current_students",
        "target_students",
        "max_students",
        "min_specialized",
        "max_specialized",
        "min_supported",
        "max_supported",
        "staff_rounding",
        "masters_rounding",
        "max_share_rounding",
        "min_share_rounding",
    ),
    bulk_actions=(
        crud.BulkAction(
            "clear-shares",
            _("clear accepted specializations"),
            "x-circle",
            method="clear_shares",
            danger=True,
        ),
        crud.BulkAction(
            "clear-current",
            _("clear current students"),
            "user-minus",
            {"current_students": None},
        ),
        crud.BulkAction(
            "clear-target",
            _("clear target students"),
            "flag",
            {"target_students": None},
        ),
        crud.BulkAction(
            "clear-max", _("clear max students"), "arrows-up-down", {"max_students": None}
        ),
    ),
    settings=FacultySettings,
    app="edu",
    name="faculties",
    model=Faculty,
    filterset=filters.FacultyFilter,
    form=forms.FacultyForm,
    ordering_fields=constants.ORDERING_FIELDS,
    title=_("faculties"),
    icon="building-library",
    export_resource=resources.FacultyResource,
    custom_form=True,
    columns=(
        crud.Column("name", _("name"), "name"),
        crud.Column("accepts", _("accepts")),
        crud.Column("capacity", _("capacity"), None, "end"),
        crud.Column("students_per_phd", _("per PhD"), "students_per_phd", "end"),
        crud.Column("staff", _("staff")),
        crud.Column("students", _("now · target · max")),
        crud.Column("contracts", _("contracts"), "contracts_count", "end"),
        crud.Column("compliance", _("compliance")),
        crud.Column("notes", _("notes"), "notes"),
    ),
)


@require_http_methods(["GET"])
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def index(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk

    queryset = Faculty.objects.for_chapter(chapter_id).with_shares().annotate_counts()

    return crud.render_index(
        request,
        RESOURCE,
        queryset,
        decorate=lambda rows: Faculty.objects.attach_reports(rows, chapter_id),
    )


@require_http_methods(["GET"])
@permission_required("app.view_faculty", raise_exception=True)
@chapter_required
def details(request: ChapterRequest, pk: int) -> HttpResponse:
    faculty = _get(request, pk, Faculty.objects.with_shares().annotate_counts())

    [faculty] = Faculty.objects.attach_reports([faculty], request.chapter.pk)

    return crud.render_details(request, RESOURCE, faculty)


@require_http_methods(["GET", "POST"])
@permission_required("app.add_faculty", raise_exception=True)
@chapter_required
def create(request: ChapterRequest) -> HttpResponse:
    return _form(request, None)


@require_http_methods(["GET", "POST"])
@permission_required("app.change_faculty", raise_exception=True)
@chapter_required
def update(request: ChapterRequest, pk: int) -> HttpResponse:
    return _form(request, _get(request, pk))


@require_http_methods(["GET", "POST"])
@permission_required("app.delete_faculty", raise_exception=True)
@chapter_required
def delete(request: ChapterRequest, pk: int) -> HttpResponse:
    faculty = _get(request, pk)

    return crud.render_delete(
        request,
        RESOURCE,
        [faculty.pk],
        delete=lambda ids: Faculty.objects.delete_many(request.chapter.pk, ids),
        names=[faculty.name],
    )


@require_POST
@permission_required("app.delete_faculty", raise_exception=True)
@chapter_required
def bulk_delete(request: ChapterRequest) -> HttpResponse:
    ids = crud.selected_ids(request)

    rows = Faculty.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)

    return crud.render_delete(
        request,
        RESOURCE,
        ids,
        delete=lambda ids: Faculty.objects.delete_many(request.chapter.pk, ids),
        names=rows.values_list("name", flat=True),
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.add_faculty", raise_exception=True)
@chapter_required
def import_file(request: ChapterRequest) -> HttpResponse:
    resource = resources.FacultyResource(chapter=request.chapter)

    return crud.render_import(
        request,
        RESOURCE,
        run=lambda dataset: Faculty.objects.import_rows(resource, dataset),
        columns=resources.FacultyResource.Meta.fields,
        sample=resource,
    )


def _form(request: AppRequest, faculty: Faculty | None) -> HttpResponse:
    """The faculty with its accepted specializations (a formset dragged into order)."""
    shares = forms.shares_formset(
        request.POST or None,
        instance=faculty or Faculty(chapter=request.chapter),
        prefix="shares",
        chapter=request.chapter,
    )

    return crud.render_form(
        request,
        RESOURCE,
        instance=faculty,
        formset=shares,
        form_kwargs={"chapter": request.chapter},
        save=lambda form: Faculty.objects.save_with_shares(form.save(commit=False), shares),
    )


def _get(request: ChapterRequest, pk: int, queryset: BaseQuerySet | None = None) -> Faculty:
    rows = queryset if queryset is not None else Faculty.objects.all()

    return get_object_or_404(rows.for_chapter(request.chapter.pk), pk=pk)


@require_POST
@permission_required("app.change_faculty", raise_exception=True)
@chapter_required
def bulk_edit(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk

    return crud.render_bulk_edit(
        request,
        RESOURCE,
        _owned(request, crud.selected_ids(request)),
        update=lambda ids, values: Faculty.objects.bulk_set(chapter_id, ids, values),
        form_kwargs={"chapter": request.chapter},
    )


@require_POST
@permission_required("app.change_faculty", raise_exception=True)
@chapter_required
def bulk_action(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk
    ids = _owned(request, crud.selected_ids(request))

    return crud.render_bulk_action(
        request,
        RESOURCE,
        ids,
        run=lambda action, ids: crud.run_bulk_action(Faculty.objects, chapter_id, action, ids),
        names=Faculty.objects.filter(pk__in=ids).values_list("name", flat=True),
    )


def _owned(request: ChapterRequest, ids: list[int]) -> list[int]:
    """The selected rows that are the current chapter's."""
    rows = Faculty.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)
    return list(rows.values_list("pk", flat=True))
