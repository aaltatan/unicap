from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from .. import filters, forms, resources
from ..constants import contract as constants
from ..decorators import chapter_required
from ..models import Contract, ContractSettings
from ..querysets.base import BaseQuerySet
from ..requests import ChapterRequest
from . import crud

RESOURCE = crud.Resource(
    bulk_fields=("faculty", "contract_type", "employment_type", "degree", "is_active"),
    bulk_actions=(
        crud.BulkAction("activate", _("activate"), "check-circle", {"is_active": True}),
        crud.BulkAction("deactivate", _("deactivate"), "no-symbol", {"is_active": False}),
        crud.BulkAction("unsign", _("unsign"), "arrow-uturn-left", {"faculty": None}),
    ),
    settings=ContractSettings,
    app="hr",
    name="contracts",
    model=Contract,
    filterset=filters.ContractFilter,
    form=forms.ContractForm,
    ordering_fields=constants.ORDERING_FIELDS,
    title=_("contracts"),
    icon="document-text",
    default_ordering=("position",),
    export_resource=resources.ContractResource,
    columns=(
        crud.Column("position", _("order"), "position", "end"),
        crud.Column("employee", _("employee"), "employee__name"),
        crud.Column("specialization", _("specialization"), "employee__specialization__name"),
        crud.Column("faculty", _("faculty"), "faculty__name"),
        crud.Column("specialization_type", _("specialization type"), "specialization_type"),
        crud.Column("degree", _("degree"), "degree"),
        crud.Column("terms", _("terms"), "contract_type"),
        crud.Column("status", _("status")),
        crud.Column("is_active", _("on"), "is_active"),
        crud.Column("notes", _("notes"), "notes"),
    ),
)


@require_http_methods(["GET"])
@permission_required("app.view_contract", raise_exception=True)
@chapter_required
def index(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk

    return crud.render_index(
        request,
        RESOURCE,
        Contract.objects.for_chapter(chapter_id).with_relations().annotate_specialization_type(),
        decorate=lambda rows: Contract.objects.attach_statuses(rows, chapter_id),
    )


@require_http_methods(["GET"])
@permission_required("app.view_contract", raise_exception=True)
@chapter_required
def details(request: ChapterRequest, pk: int) -> HttpResponse:
    contract = _get(request, pk, Contract.objects.with_relations().annotate_specialization_type())

    [contract] = Contract.objects.attach_statuses([contract], request.chapter.pk)

    return crud.render_details(request, RESOURCE, contract)


@require_http_methods(["GET", "POST"])
@permission_required("app.add_contract", raise_exception=True)
@chapter_required
def create(request: ChapterRequest) -> HttpResponse:
    return crud.render_form(
        request,
        RESOURCE,
        save=_save,
        form_kwargs={"chapter": request.chapter},
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.change_contract", raise_exception=True)
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
@permission_required("app.delete_contract", raise_exception=True)
@chapter_required
def delete(request: ChapterRequest, pk: int) -> HttpResponse:
    contract = _get(request, pk, Contract.objects.with_relations())

    return crud.render_delete(
        request,
        RESOURCE,
        [contract.pk],
        delete=lambda ids: Contract.objects.delete_many(request.chapter.pk, ids),
        names=[str(contract)],
    )


@require_POST
@permission_required("app.delete_contract", raise_exception=True)
@chapter_required
def bulk_delete(request: ChapterRequest) -> HttpResponse:
    ids = crud.selected_ids(request)

    rows = Contract.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)

    return crud.render_delete(
        request,
        RESOURCE,
        ids,
        delete=lambda ids: Contract.objects.delete_many(request.chapter.pk, ids),
        names=rows.values_list("employee__name", flat=True),
    )


@require_POST
@permission_required("app.change_contract", raise_exception=True)
@chapter_required
def toggle(request: ChapterRequest, pk: int) -> HttpResponse:
    return crud.render_toggle(request, _get(request, pk), toggle=Contract.objects.toggle_active)


@require_http_methods(["GET", "POST"])
@permission_required("app.add_contract", raise_exception=True)
@chapter_required
def import_file(request: ChapterRequest) -> HttpResponse:
    resource = resources.ContractResource(chapter=request.chapter)

    return crud.render_import(
        request,
        RESOURCE,
        run=lambda dataset: Contract.objects.import_rows(resource, dataset),
        columns=resources.ContractResource.Meta.fields,
        sample=resource,
    )


def _save(form: forms.ContractForm) -> Contract:
    return Contract.objects.save_contract(form.save(commit=False))


def _get(request: ChapterRequest, pk: int, queryset: BaseQuerySet | None = None) -> Contract:
    rows = queryset if queryset is not None else Contract.objects.all()

    return get_object_or_404(rows.for_chapter(request.chapter.pk), pk=pk)


@require_POST
@permission_required("app.change_contract", raise_exception=True)
@chapter_required
def bulk_edit(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk

    return crud.render_bulk_edit(
        request,
        RESOURCE,
        _owned(request, crud.selected_ids(request)),
        update=lambda ids, values: Contract.objects.bulk_set(chapter_id, ids, values),
        form_kwargs={"chapter": request.chapter},
    )


@require_POST
@permission_required("app.change_contract", raise_exception=True)
@chapter_required
def bulk_action(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk
    ids = _owned(request, crud.selected_ids(request))

    return crud.render_bulk_action(
        request,
        RESOURCE,
        ids,
        run=lambda action, ids: crud.run_bulk_action(Contract.objects, chapter_id, action, ids),
        names=Contract.objects.filter(pk__in=ids).values_list("employee__name", flat=True),
    )


def _owned(request: ChapterRequest, ids: list[int]) -> list[int]:
    """The selected rows that are the current chapter's."""
    rows = Contract.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)
    return list(rows.values_list("pk", flat=True))
