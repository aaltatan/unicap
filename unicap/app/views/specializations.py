from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from .. import filters, forms, resources
from ..constants import specialization as constants
from ..decorators import chapter_required
from ..models import Employee, Specialization, SpecializationSettings
from ..querysets.base import BaseQuerySet
from ..requests import ChapterRequest
from . import crud

RESOURCE = crud.Resource(
    bulk_fields=("is_active",),
    bulk_actions=(
        crud.BulkAction("activate", _("activate"), "check-circle", {"is_active": True}),
        crud.BulkAction("deactivate", _("deactivate"), "no-symbol", {"is_active": False}),
    ),
    settings=SpecializationSettings,
    app="edu",
    name="specializations",
    model=Specialization,
    filterset=filters.SpecializationFilter,
    form=forms.SpecializationForm,
    ordering_fields=constants.ORDERING_FIELDS,
    title=_("specializations"),
    icon="academic-cap",
    export_resource=resources.SpecializationResource,
    columns=(
        crud.Column("name", _("name"), "name"),
        crud.Column("is_active", _("active"), "is_active"),
        crud.Column("faculties", _("faculties"), "faculties_count", "end"),
        crud.Column("employees", _("employees"), "employees_count", "end"),
        crud.Column("notes", _("notes"), "notes"),
    ),
)


@require_http_methods(["GET"])
@permission_required("app.view_specialization", raise_exception=True)
@chapter_required
def index(request: ChapterRequest) -> HttpResponse:
    queryset = Specialization.objects.for_chapter(request.chapter.pk).annotate_usage()

    return crud.render_index(request, RESOURCE, queryset)


@require_http_methods(["GET"])
@permission_required("app.view_specialization", raise_exception=True)
@chapter_required
def details(request: ChapterRequest, pk: int) -> HttpResponse:
    specialization = _get(request, pk, Specialization.objects.annotate_usage())

    chapter_id = request.chapter.pk

    employees = (
        Employee.objects.for_chapter(chapter_id)
        .holding(specialization.pk)
        .with_contract()
        .annotate_specialization_type()
    )

    return crud.render_details(
        request,
        RESOURCE,
        specialization,
        {
            "shares": specialization.shares.select_related("faculty").order_by("faculty__name"),
            "employees": Employee.objects.attach_statuses(employees, chapter_id),
        },
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.add_specialization", raise_exception=True)
@chapter_required
def create(request: ChapterRequest) -> HttpResponse:
    return crud.render_form(
        request,
        RESOURCE,
        save=_save,
        form_kwargs={"chapter": request.chapter},
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.change_specialization", raise_exception=True)
@chapter_required
def update(request: ChapterRequest, pk: int) -> HttpResponse:
    return crud.render_form(
        request,
        RESOURCE,
        save=_save,
        instance=_get(request, pk),
        form_kwargs={"chapter": request.chapter},
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.delete_specialization", raise_exception=True)
@chapter_required
def delete(request: ChapterRequest, pk: int) -> HttpResponse:
    specialization = _get(request, pk)

    return crud.render_delete(
        request,
        RESOURCE,
        [specialization.pk],
        delete=lambda ids: Specialization.objects.delete_many(request.chapter.pk, ids),
        names=[specialization.name],
    )


@require_POST
@permission_required("app.delete_specialization", raise_exception=True)
@chapter_required
def bulk_delete(request: ChapterRequest) -> HttpResponse:
    ids = crud.selected_ids(request)

    rows = Specialization.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)

    return crud.render_delete(
        request,
        RESOURCE,
        ids,
        delete=lambda ids: Specialization.objects.delete_many(request.chapter.pk, ids),
        names=rows.values_list("name", flat=True),
    )


@require_POST
@permission_required("app.change_specialization", raise_exception=True)
@chapter_required
def toggle(request: ChapterRequest, pk: int) -> HttpResponse:
    return crud.render_toggle(
        request, _get(request, pk), toggle=Specialization.objects.toggle_active
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.add_specialization", raise_exception=True)
@chapter_required
def import_file(request: ChapterRequest) -> HttpResponse:
    resource = resources.SpecializationResource(chapter=request.chapter)

    return crud.render_import(
        request,
        RESOURCE,
        run=lambda dataset: Specialization.objects.import_rows(resource, dataset),
        columns=resources.SpecializationResource.Meta.fields,
        sample=resource,
    )


def _save(form: forms.SpecializationForm) -> Specialization:
    return Specialization.objects.save_validated(form.save(commit=False))


def _get(request: ChapterRequest, pk: int, queryset: BaseQuerySet | None = None) -> Specialization:
    rows = queryset if queryset is not None else Specialization.objects.all()

    return get_object_or_404(rows.for_chapter(request.chapter.pk), pk=pk)


@require_POST
@permission_required("app.change_specialization", raise_exception=True)
@chapter_required
def bulk_edit(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk

    return crud.render_bulk_edit(
        request,
        RESOURCE,
        _owned(request, crud.selected_ids(request)),
        update=lambda ids, values: Specialization.objects.bulk_set(chapter_id, ids, values),
        form_kwargs={"chapter": request.chapter},
    )


@require_POST
@permission_required("app.change_specialization", raise_exception=True)
@chapter_required
def bulk_action(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk
    ids = _owned(request, crud.selected_ids(request))

    return crud.render_bulk_action(
        request,
        RESOURCE,
        ids,
        run=lambda action, ids: crud.run_bulk_action(
            Specialization.objects, chapter_id, action, ids
        ),
        names=Specialization.objects.filter(pk__in=ids).values_list("name", flat=True),
    )


def _owned(request: ChapterRequest, ids: list[int]) -> list[int]:
    """The selected rows that are the current chapter's."""
    rows = Specialization.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)
    return list(rows.values_list("pk", flat=True))
