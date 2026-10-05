"""Functional building blocks every resource's views are made of.

Each resource (faculties, employees, ...) describes itself once with a `Resource`; its
function-based views then call one of these helpers with the queryset and the manager
call that does the work:

```python
@require_http_methods(["GET"])
@permission_required("app.view_faculty", raise_exception=True)
def index(request: AppRequest) -> HttpResponse:
    return crud.render_index(request, RESOURCE, Faculty.objects.for_chapter(request.chapter.pk))
```

The helpers parse input, pick a template and build the response (HTMX headers included);
they hold no business rule: writes go through the callable they are given, and a
`DomainError` / `UserError` it raises is shown on the form or as a message.
"""

import copy
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Model, QuerySet
from django.forms import BaseFormSet
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header, urlencode
from django.utils.text import get_valid_filename
from django.utils.translation import gettext as _
from django_filters import FilterSet
from import_export.resources import ModelResource
from tablib import Dataset

from unicap.domain import DomainError

from ..choices import PER_PAGE_CHOICES, BackupScopeChoices, BackupSectionChoices
from ..exceptions import UserError
from ..managers import ViewSettings
from ..managers.base import ChapterOwnedManager
from ..models import AppSettings, SectionSettings
from ..requests import AppRequest
from ..resources import sample_file
from ..resources.base import TranslatedResource
from ..texts import error_text
from ..utils import StrOrPromise, parse_ordering

if TYPE_CHECKING:
    from ..querysets.base import BaseQuerySet

EXPORT_FORMATS = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
}

TABLE_TARGET = "table"

# what the reset in the filters button keeps: only the filters go
KEPT_ON_RESET = ("q", "ordering", "per_page")

Save = Callable[[Any], Model]  # takes the resource's own form class


@dataclass(frozen=True)
class Column:
    """A table column: `key` names its cells (`data-col`), `sort` its ordering field."""

    key: str
    label: StrOrPromise
    sort: str | None = None
    align: str = "start"


@dataclass(frozen=True)
class BulkAction:
    """A one-click change to the selected rows: set `values` on each, or run `method`.

    `method` names a manager method `method(chapter_id, ids) -> int` (rows changed).
    """

    name: str
    label: StrOrPromise
    icon: str
    values: Mapping[str, Any] = field(default_factory=dict)
    method: str = ""
    danger: bool = False


@dataclass(frozen=True)
class Resource:
    """How one model appears in the UI: its urls, filters, form, export and templates.

    Urls are named `<namespace>:index|create|update|delete|details|bulk-delete|import`, and
    `bulk-edit|bulk-action` with `bulk_fields` (changed together in a form) and `bulk_actions`.
    Templates live in `components/<app>/<name>/`: `rows.html` (table head and rows),
    `details.html`, optionally `form.html` (else the generic field list) and `actions.html`
    (more buttons on each row, with `row_actions`).
    """

    app: str
    name: str
    model: type[Model]
    filterset: type[FilterSet]
    form: type[forms.ModelForm]
    ordering_fields: Mapping[str, StrOrPromise]
    title: StrOrPromise
    icon: str
    columns: tuple[Column, ...] = ()
    default_ordering: tuple[str, ...] = ()
    export_resource: type[ModelResource] | None = None
    importable: bool = True
    custom_form: bool = False
    row_actions: bool = False  # its own buttons on each row: `actions.html`
    settings: type[SectionSettings] | None = (
        None  # its `SectionSettings`: rows per page, modal sizes
    )
    bulk_fields: tuple[str, ...] = ()  # the form's fields the selected rows can share
    bulk_actions: tuple[BulkAction, ...] = ()
    extra_urls: Mapping[str, str] = field(default_factory=dict)

    @property
    def namespace(self) -> str:
        """`edu:faculties`, or just `chapters` when the app is the resource."""
        return self.app if self.app == self.name else f"{self.app}:{self.name}"

    @property
    def codename(self) -> str:
        return self.model._meta.model_name or ""  # noqa: SLF001

    def url(self, action: str, **kwargs: Any) -> str:
        return reverse(f"{self.namespace}:{action}", kwargs=kwargs or None)

    def permission(self, action: str) -> str:
        return f"{self.app}.{action}_{self.codename}"

    @property
    def templates(self) -> str:
        return f"components/{self.app}/{self.name}"

    @property
    def url_index(self) -> str:
        return self.url("index")

    @property
    def url_create(self) -> str:
        return self.url("create")

    @property
    def url_bulk_delete(self) -> str:
        return self.url("bulk-delete")

    @property
    def url_bulk_edit(self) -> str:
        return self.url("bulk-edit")

    @property
    def url_bulk_action(self) -> str:
        return self.url("bulk-action")

    @property
    def url_import(self) -> str:
        return self.url("import")

    @property
    def columns_json(self) -> str:
        """The columns for the "columns" menu (reorder / hide), as JSON."""
        return json.dumps([{"key": c.key, "label": str(c.label)} for c in self.columns])


# --- reading -------------------------------------------------------------------------


def render_index(  # noqa: PLR0913 - the request, what to list and how to show it
    request: AppRequest,
    resource: Resource,
    queryset: QuerySet,
    *,
    decorate: Callable[[list[Any]], list[Any]] | None = None,
    extra_context: Mapping[str, Any] | None = None,
    export_queryset: Callable[[QuerySet], Iterable[Model]] | None = None,
) -> HttpResponse:
    """List `queryset`: search, filters, sorting, pages; an export; or just the table.

    The whole page on a normal request; only the table when HTMX targets it (search,
    filters, sorting, paging, refreshes after a write).

    Args:
        request: the GET request (`q`, filters, `ordering`, `page`, `per_page`, `export`).
        resource: what is listed.
        queryset: every row the user may see (the current chapter's).
        decorate: adds computed values (domain results) to the rows of the page.
        extra_context: more template values.
        export_queryset: the rows to export (default: every filtered row).
    """
    params = request.GET

    filterset = resource.filterset(params or None, queryset=queryset, request=request)

    rows = cast(
        "BaseQuerySet", filterset.qs if filterset.is_bound and filterset.is_valid() else queryset
    )

    ordering = parse_ordering(params.get("ordering")) or list(resource.default_ordering)

    rows = rows.order_by_fields(ordering, resource.ordering_fields)

    if not rows.ordered:  # aggregate annotations drop Meta.ordering: keep pages stable
        rows = rows.order_by(*(resource.model._meta.ordering or ()), "pk")  # noqa: SLF001

    if (extension := params.get("export")) in EXPORT_FORMATS and resource.export_resource:
        exported = export_queryset(rows) if export_queryset else rows
        return _export(resource, exported, extension, request)

    per_page = _per_page(params.get("per_page"), _view_settings(resource).per_page)

    page = Paginator(rows, per_page).get_page(params.get("page"))

    # unnarrowed, the page's count is the total: one COUNT instead of two
    total = queryset.count() if _is_narrowed(filterset) else page.paginator.count

    objects = list(page.object_list)

    context = {
        "resource": resource,
        "model": resource.model,
        "filterset": filterset,
        "page": page,
        "objects": decorate(objects) if decorate else objects,
        "total": total,
        "filtered": page.paginator.count,
        "per_page": per_page,
        "per_page_choices": PER_PAGE_CHOICES,
        "active_filters": _active_filters(filterset),
        "filters_reset_url": _without_filters(request, resource.url("index")),
        "index_url": resource.url("index"),
        "page_title": resource.title,
        **_permissions(request, resource),
        **_backups(request, resource),
        **(extra_context or {}),
    }

    if request.htmx and request.htmx.target == TABLE_TARGET:
        return render(request, "app/crud/table.html", context)

    return render(request, "app/crud/index.html", context)


def render_details(
    request: AppRequest,
    resource: Resource,
    obj: Model,
    extra_context: Mapping[str, Any] | None = None,
) -> HttpResponse:
    """Everything about one row, in the modal (or a page without HTMX)."""
    context = {
        "resource": resource,
        "obj": obj,
        "model": resource.model,
        "page_title": str(obj),
        "modal_width": _view_settings(resource).details_modal_size,
        **_permissions(request, resource),
        **(extra_context or {}),
    }

    template = "app/crud/details-modal.html" if request.htmx else "app/crud/details.html"

    return render(request, template, context)


# --- writing -------------------------------------------------------------------------


def render_form(  # noqa: PLR0913 - the request, the form and what saving means
    request: AppRequest,
    resource: Resource,
    *,
    save: Save,
    instance: Model | None = None,
    form_kwargs: Mapping[str, Any] | None = None,
    formset: BaseFormSet | None = None,
    extra_context: Mapping[str, Any] | None = None,
) -> HttpResponse:
    """Create (no `instance`) or update a row in the modal.

    On success the modal closes (or empties for the next record with "save & new") and
    every table and board listening for `refresh` redraws.

    Args:
        request: GET shows the form, POST saves it.
        resource: what is edited.
        save: the manager call that saves the valid form (and `formset`); it may raise
            `DomainError` / `UserError`, shown on the form and nothing is saved.
        instance: the row to update (None: a new one).
        form_kwargs: more arguments for the form (the chapter).
        formset: nested rows edited with the form (a faculty's shares).
        extra_context: more template values.
    """
    adding = instance is None

    form = resource.form(
        request.POST or None,
        request.FILES or None,
        instance=instance,
        **(form_kwargs or {}),
    )

    if request.method == "POST" and form.is_valid() and (formset is None or formset.is_valid()):
        try:
            obj = save(form)
        except (DomainError, UserError) as error:
            _restore_adding(form, adding=adding)
            form.add_error(None, error_text(error))
        else:
            message = _("%(name)s created.") if adding else _("%(name)s saved.")
            messages.success(request, message % {"name": obj})
            return _after_save(request, resource, again="save_and_new" in request.POST)

    context = {
        "resource": resource,
        "form": form,
        "formset": formset,
        "instance": instance,
        "adding": adding,
        "action_url": resource.url("create")
        if adding
        else resource.url("update", pk=getattr(instance, "pk", None)),
        "page_title": _("new %(what)s") % {"what": resource.model._meta.verbose_name}  # noqa: SLF001
        if adding
        else str(instance),
        "modal_width": _view_settings(resource).form_modal_size,
        **(extra_context or {}),
    }

    template = "app/crud/form-modal.html" if request.htmx else "app/crud/form.html"

    return render(request, template, context)


def render_delete(
    request: AppRequest,
    resource: Resource,
    ids: list[int],
    *,
    delete: Callable[[list[int]], int],
    names: Iterable[str],
) -> HttpResponse:
    """Confirm (GET, or POST without `confirmed`), then delete every id in one transaction."""
    names = list(names)

    if request.method == "POST" and request.POST.get("confirmed") and ids:
        try:
            deleted = delete(ids)
        except (DomainError, UserError) as error:
            messages.error(request, error_text(error))
            return _close_modal()

        messages.success(request, _("%(count)s deleted.") % {"count": deleted})

        return _after_save(request, resource, again=False)

    context = {
        "resource": resource,
        "ids": ids,
        "names": names,
        "action_url": request.path,
    }

    return render(request, "app/crud/delete-modal.html", context)


def render_toggle(
    request: AppRequest,
    obj: Model,
    *,
    toggle: Callable[[Model], Model],
) -> HttpResponse:
    """Switch a row on or off, then let tables and the board redraw."""
    try:
        toggle(obj)
    except (DomainError, UserError) as error:
        messages.error(request, error_text(error))
    else:
        message = (
            _("%(name)s is on.") if getattr(obj, "is_active", False) else _("%(name)s is off.")
        )
        messages.success(request, message % {"name": obj})

    return trigger(HttpResponse(""), refresh=True)


def render_import(
    request: AppRequest,
    resource: Resource,
    *,
    run: Callable[[Any], int],
    columns: Iterable[str],
    sample: TranslatedResource | None = None,
) -> HttpResponse:
    """Import an xlsx / csv file: `run(dataset)` saves every row, or none.

    Args:
        request: GET shows the form (or, with `sample=xlsx|csv`, downloads a sample file),
            POST imports the uploaded `file`.
        resource: what is imported.
        run: saves the rows (a manager or resource call); returns how many were saved and
            raises `UserError` / `DomainError` to refuse the whole file.
        columns: the columns the file holds (shown as a hint).
        sample: writes the sample file to fill in (none: no sample is offered).
    """
    if sample and (extension := request.GET.get("sample", "")) in EXPORT_FORMATS:
        name = _("%(what)s sample") % {"what": resource.title}
        return _download(sample_file(sample, extension), extension, name)

    errors: list[str] = []

    upload = request.FILES.get("file")

    if request.method == "POST":
        if upload is None:
            errors.append(_("Choose a file."))
        else:
            try:
                dataset = read_dataset(upload.name or "", upload.read())
                saved = run(dataset)
            except (DomainError, UserError, ValueError) as error:
                errors.extend(error_text(error).splitlines() or [error_text(error)])
            else:
                messages.success(request, _("%(count)s row(s) imported.") % {"count": saved})
                return _close_modal(refresh=True)

    context = {
        "resource": resource,
        "errors": errors,
        "columns": list(columns),
        "has_sample": sample is not None,
        "action_url": resource.url("import"),
        "page_title": _("import %(what)s") % {"what": resource.title},
    }

    return render(request, "app/crud/import-modal.html", context)


def read_dataset(filename: str, content: bytes) -> Dataset:
    """A tablib dataset from an uploaded xlsx or csv file.

    Raises:
        ValueError: another kind of file, or one that cannot be read.
    """
    extension = filename.rsplit(".", 1)[-1].lower()

    if extension not in EXPORT_FORMATS:
        msg = _("Only .xlsx and .csv files can be imported, not %(name)s.") % {"name": filename}
        raise ValueError(msg)

    try:
        if extension == "csv":
            return Dataset().load(content.decode("utf-8-sig"), format="csv")

        return Dataset().load(content, format="xlsx")
    except Exception as error:  # tablib raises many kinds
        msg = _("%(name)s cannot be read: %(error)s") % {"name": filename, "error": error}
        raise ValueError(msg) from error


def trigger(response: HttpResponse, **events: object) -> HttpResponse:
    """Add HTMX client events (`HX-Trigger`), e.g. `trigger(response, refresh=True)`."""
    existing = json.loads(response.headers.get("HX-Trigger", "{}") or "{}")

    existing.update(events)

    response["HX-Trigger"] = json.dumps(existing)

    return response


def render_bulk_edit(
    request: AppRequest,
    resource: Resource,
    ids: list[int],
    *,
    update: Callable[[list[int], dict[str, Any]], int],
    form_kwargs: Mapping[str, Any] | None = None,
) -> HttpResponse:
    """Change the checked fields of every selected row at once (all rows, or none).

    Args:
        request: a POST holding the selected `ids` (and, to apply, `confirmed`).
        resource: whose `bulk_fields` are offered, drawn as its form draws them.
        ids: the selected rows.
        update: `update(ids, values)` saves the values on the rows; returns how many.
        form_kwargs: what the resource's form needs (its chapter).
    """
    confirmed = bool(request.POST.get("confirmed"))

    form = _bulk_form(resource, request.POST if confirmed else None, form_kwargs or {})

    if confirmed and ids and form.is_valid():
        values = {
            name: form.cleaned_data[name]
            for name in resource.bulk_fields
            if form.cleaned_data.get(f"apply_{name}")
        }

        if not values:
            form.add_error(None, _("check the fields to change."))
        else:
            try:
                changed = update(ids, values)
            except (DomainError, UserError) as error:
                form.add_error(None, error_text(error))
            else:
                messages.success(request, _("%(count)s row(s) changed.") % {"count": changed})
                return _close_modal(refresh=True)

    rows = [(form[f"apply_{name}"], form[name]) for name in resource.bulk_fields]

    return render(
        request,
        "app/crud/bulk-edit-modal.html",
        {"resource": resource, "form": form, "rows": rows, "ids": ids},
    )


def render_bulk_action(
    request: AppRequest,
    resource: Resource,
    ids: list[int],
    *,
    run: Callable[[BulkAction, list[int]], int],
    names: Iterable[str],
) -> HttpResponse:
    """Confirm, then apply one of the resource's `bulk_actions` to the selected rows."""
    action = next((a for a in resource.bulk_actions if a.name == request.POST.get("action")), None)

    if action is None:
        raise Http404

    if request.POST.get("confirmed") and ids:
        try:
            changed = run(action, ids)
        except (DomainError, UserError) as error:
            messages.error(request, error_text(error))
            return _close_modal()

        messages.success(request, _("%(count)s row(s) changed.") % {"count": changed})
        return _close_modal(refresh=True)

    return render(
        request,
        "app/crud/bulk-action-modal.html",
        {"resource": resource, "action": action, "ids": ids, "names": list(names)},
    )


def run_bulk_action(
    manager: ChapterOwnedManager,
    chapter_id: int,
    action: BulkAction,
    ids: list[int],
) -> int:
    """A bulk action on a chapter's rows: its manager `method`, or `bulk_set` its `values`."""
    if action.method:
        return getattr(manager, action.method)(chapter_id, ids)

    return manager.bulk_set(chapter_id, ids, dict(action.values))


def selected_ids(request: AppRequest) -> list[int]:
    """The row ids checked in a table (`<input name="ids">`)."""
    return [int(value) for value in request.POST.getlist("ids") if value.isdigit()]


# --- private helpers -----------------------------------------------------------------


def _after_save(request: AppRequest, resource: Resource, *, again: bool) -> HttpResponse:
    if not request.htmx:
        return redirect(resource.url("index"))

    response = _close_modal(refresh=True)

    if again:  # "save & new": the client opens a blank form right away
        trigger(response, **{"open-modal": resource.url("create")})

    return response


def _close_modal(*, refresh: bool = False) -> HttpResponse:
    events: dict[str, object] = {"close-modal": True}

    if refresh:
        events["refresh"] = True

    return trigger(HttpResponse(""), **events)


def _restore_adding(form: forms.ModelForm, *, adding: bool) -> None:
    """After a rolled-back create, the instance must look unsaved again."""
    if adding:
        form.instance.pk = None
        form.instance._state.adding = True  # noqa: SLF001


def _permissions(request: AppRequest, resource: Resource) -> dict[str, bool]:
    """What the user may do here: `perms_add`, `perms_change`, `perms_delete`."""
    return {
        f"perms_{action}": request.user.has_perm(resource.permission(action))
        for action in ("add", "change", "delete")
    }


def _bulk_form(
    resource: Resource,
    data: Mapping[str, Any] | None,
    form_kwargs: Mapping[str, Any],
) -> forms.Form:
    """The bulk fields, as the resource's form draws them, each with an "apply" box.

    A plain form: only the checked values are read, nothing else of the model is validated.
    """
    drawn = resource.form(**form_kwargs).fields

    form = forms.Form(data)

    for name in resource.bulk_fields:
        bulk_field = copy.deepcopy(drawn[name])
        bulk_field.required = False
        form.fields[f"apply_{name}"] = forms.BooleanField(required=False, label=bulk_field.label)
        form.fields[name] = bulk_field

    return form


def _backups(request: AppRequest, resource: Resource) -> dict[str, object]:
    """The table's backup: its section (or, on the chapters' page, the chapter) and rights."""
    if resource.name in BackupSectionChoices.values:
        scope, section = BackupScopeChoices.SECTION, resource.name
    elif resource.name == "chapters":
        scope, section = BackupScopeChoices.CHAPTER, ""
    else:
        return {"backup_scope": ""}

    return {
        "backup_scope": scope,
        "backup_section": section,
        "perms_backup": request.user.has_perm("app.add_backup"),
        "perms_view_backups": request.user.has_perm("app.view_backup"),
    }


def _per_page(value: str | None, default: int) -> int:
    if value and value.isdigit() and int(value) in PER_PAGE_CHOICES:
        return int(value)

    return default


def _view_settings(resource: Resource) -> ViewSettings:
    """The section's settings, or the app's when the resource has none."""
    if resource.settings is not None:
        return resource.settings.objects.effective()

    app = AppSettings.get_solo()

    return ViewSettings(app.per_page, app.modal_size, app.modal_size)


def _active_filters(filterset: FilterSet) -> int:
    """How many filters (search excluded) hold a value: the badge on the filters button."""
    if not filterset.is_bound or not filterset.is_valid():
        return 0

    return sum(
        1 for name, value in filterset.form.cleaned_data.items() if name != "q" and _holds(value)
    )


def _is_narrowed(filterset: FilterSet) -> bool:
    """A search or a filter leaves some rows out (an invalid one filters nothing)."""
    if not filterset.is_bound or not filterset.is_valid():
        return False

    return any(_holds(value) for value in filterset.form.cleaned_data.values())


def _holds(value: object) -> bool:
    """A filter's cleaned value narrows the rows: not empty (`0` does, an empty choice not)."""
    if value is None or value == "":
        return False

    if isinstance(value, (list, tuple, set, QuerySet)):
        return bool(value)  # an unchosen multiple choice cleans to an empty one

    return True


def _without_filters(request: AppRequest, index_url: str) -> str:
    """The table as it is, without its filters: the search, sorting and page size stay."""
    kept = {key: request.GET[key] for key in KEPT_ON_RESET if request.GET.get(key)}

    return f"{index_url}?{urlencode(kept)}" if kept else index_url


def _export(
    resource: Resource,
    rows: Iterable[Model],
    extension: str,
    request: AppRequest,
) -> HttpResponse:
    assert resource.export_resource is not None  # noqa: S101 - checked by the caller

    exporter = resource.export_resource(chapter=getattr(request, "chapter", None))

    dataset = exporter.export(queryset=rows)

    content = dataset.export(extension)

    if extension == "csv":
        content = "﻿" + content  # a BOM: Excel then reads the CSV as UTF-8 (Arabic)

    return _download(content, extension, str(resource.title))


def _download(content: bytes | str, extension: str, name: str) -> HttpResponse:
    """A file to save, named `<name>.<extension>`."""
    response = HttpResponse(content, content_type=EXPORT_FORMATS[extension])

    filename = f"{get_valid_filename(name)}.{extension}"

    response["Content-Disposition"] = content_disposition_header(
        as_attachment=True,
        filename=filename,
    )

    return response
