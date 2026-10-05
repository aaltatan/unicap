from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from .. import filters, forms, resources
from ..constants import employee as constants
from ..decorators import chapter_required
from ..models import Employee, EmployeeSettings
from ..querysets.base import BaseQuerySet
from ..requests import ChapterRequest
from . import crud

RESOURCE = crud.Resource(
    bulk_fields=("specialization", "is_active"),
    bulk_actions=(
        crud.BulkAction("activate", _("activate"), "check-circle", {"is_active": True}),
        crud.BulkAction("deactivate", _("deactivate"), "no-symbol", {"is_active": False}),
    ),
    settings=EmployeeSettings,
    app="hr",
    name="employees",
    model=Employee,
    filterset=filters.EmployeeFilter,
    form=forms.EmployeeForm,
    ordering_fields=constants.ORDERING_FIELDS,
    title=_("employees"),
    icon="users",
    export_resource=resources.EmployeeResource,
    columns=(
        crud.Column("name", _("name"), "name"),
        crud.Column("specialization", _("specialization"), "specialization__name"),
        crud.Column("specialization_type", _("specialization type"), "specialization_type"),
        crud.Column("faculty", _("faculty"), "contract__faculty__name"),
        crud.Column("terms", _("terms")),
        crud.Column("status", _("status")),
        crud.Column("is_active", _("active"), "is_active"),
        crud.Column("notes", _("notes"), "notes"),
    ),
)


@require_http_methods(["GET"])
@permission_required("app.view_employee", raise_exception=True)
@chapter_required
def index(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk

    return crud.render_index(
        request,
        RESOURCE,
        Employee.objects.for_chapter(chapter_id).with_contract().annotate_specialization_type(),
        decorate=lambda rows: Employee.objects.attach_statuses(rows, chapter_id),
    )


@require_http_methods(["GET"])
@permission_required("app.view_employee", raise_exception=True)
@chapter_required
def details(request: ChapterRequest, pk: int) -> HttpResponse:
    employee = _get(request, pk, Employee.objects.with_contract().annotate_specialization_type())

    [employee] = Employee.objects.attach_statuses([employee], request.chapter.pk)

    return crud.render_details(
        request,
        RESOURCE,
        employee,
        {"excluded_faculties": employee.excluded_faculties.all()},
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.add_employee", raise_exception=True)
@chapter_required
def create(request: ChapterRequest) -> HttpResponse:
    return crud.render_form(
        request,
        RESOURCE,
        save=_save,
        form_kwargs={"chapter": request.chapter},
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.change_employee", raise_exception=True)
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
@permission_required("app.delete_employee", raise_exception=True)
@chapter_required
def delete(request: ChapterRequest, pk: int) -> HttpResponse:
    employee = _get(request, pk)

    return crud.render_delete(
        request,
        RESOURCE,
        [employee.pk],
        delete=lambda ids: Employee.objects.delete_many(request.chapter.pk, ids),
        names=[employee.name],
    )


@require_POST
@permission_required("app.delete_employee", raise_exception=True)
@chapter_required
def bulk_delete(request: ChapterRequest) -> HttpResponse:
    ids = crud.selected_ids(request)

    rows = Employee.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)

    return crud.render_delete(
        request,
        RESOURCE,
        ids,
        delete=lambda ids: Employee.objects.delete_many(request.chapter.pk, ids),
        names=rows.values_list("name", flat=True),
    )


@require_POST
@permission_required("app.change_employee", raise_exception=True)
@chapter_required
def toggle(request: ChapterRequest, pk: int) -> HttpResponse:
    return crud.render_toggle(request, _get(request, pk), toggle=Employee.objects.toggle_active)


@require_http_methods(["GET", "POST"])
@permission_required("app.add_employee", raise_exception=True)
@chapter_required
def import_file(request: ChapterRequest) -> HttpResponse:
    resource = resources.EmployeeResource(chapter=request.chapter)

    return crud.render_import(
        request,
        RESOURCE,
        run=lambda dataset: Employee.objects.import_rows(resource, dataset),
        columns=resources.EmployeeResource.Meta.fields,
        sample=resource,
    )


def _save(form: forms.EmployeeForm) -> Employee:
    return Employee.objects.save_validated(
        form.save(commit=False),
        after=lambda _employee: form.save_m2m(),  # the excluded faculties, once it has an id
    )


def _get(request: ChapterRequest, pk: int, queryset: BaseQuerySet | None = None) -> Employee:
    rows = queryset if queryset is not None else Employee.objects.all()

    return get_object_or_404(rows.for_chapter(request.chapter.pk), pk=pk)


@require_POST
@permission_required("app.change_employee", raise_exception=True)
@chapter_required
def bulk_edit(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk

    return crud.render_bulk_edit(
        request,
        RESOURCE,
        _owned(request, crud.selected_ids(request)),
        update=lambda ids, values: Employee.objects.bulk_set(chapter_id, ids, values),
        form_kwargs={"chapter": request.chapter},
    )


@require_POST
@permission_required("app.change_employee", raise_exception=True)
@chapter_required
def bulk_action(request: ChapterRequest) -> HttpResponse:
    chapter_id = request.chapter.pk
    ids = _owned(request, crud.selected_ids(request))

    return crud.render_bulk_action(
        request,
        RESOURCE,
        ids,
        run=lambda action, ids: crud.run_bulk_action(Employee.objects, chapter_id, action, ids),
        names=Employee.objects.filter(pk__in=ids).values_list("name", flat=True),
    )


def _owned(request: ChapterRequest, ids: list[int]) -> list[int]:
    """The selected rows that are the current chapter's."""
    rows = Employee.objects.for_chapter(request.chapter.pk).filter(pk__in=ids)
    return list(rows.values_list("pk", flat=True))
