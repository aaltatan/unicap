from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_http_methods, require_POST

from unicap.domain import DomainError

from .. import filters, forms, resources
from ..constants import chapter as constants
from ..exceptions import UserError
from ..middlewares import SESSION_CHAPTER
from ..models import Chapter, ChapterSettings
from ..requests import AppRequest
from ..texts import error_text
from . import crud

RESOURCE = crud.Resource(
    bulk_fields=("max_students",),
    bulk_actions=(
        crud.BulkAction(
            "clear-max", _("clear max students"), "arrows-up-down", {"max_students": None}
        ),
    ),
    settings=ChapterSettings,
    app="chapters",
    name="chapters",
    model=Chapter,
    filterset=filters.ChapterFilter,
    form=forms.ChapterForm,
    ordering_fields=constants.ORDERING_FIELDS,
    title=gettext_lazy("chapters"),
    icon="rectangle-stack",
    export_resource=resources.ChapterResource,
    importable=False,
    columns=(
        crud.Column("name", gettext_lazy("name"), "name"),
        crud.Column("max_students", gettext_lazy("max students"), "max_students", "end"),
        crud.Column("faculties", gettext_lazy("faculties"), "faculties_count", "end"),
        crud.Column("employees", gettext_lazy("employees"), "employees_count", "end"),
        crud.Column("contracts", gettext_lazy("contracts"), "contracts_count", "end"),
        crud.Column("notes", gettext_lazy("notes"), "notes"),
        crud.Column("actions", gettext_lazy("chapter actions")),
    ),
)


@require_http_methods(["GET"])
@permission_required("app.view_chapter", raise_exception=True)
def index(request: AppRequest) -> HttpResponse:
    return crud.render_index(request, RESOURCE, Chapter.objects.annotate_counts())


@require_http_methods(["GET"])
@permission_required("app.view_chapter", raise_exception=True)
def details(request: AppRequest, pk: int) -> HttpResponse:
    chapter = get_object_or_404(Chapter.objects.annotate_counts(), pk=pk)

    try:
        report = Chapter.objects.get_snapshot(chapter.pk).report()
    except DomainError as error:
        report, problem = None, error_text(error)
    else:
        problem = ""

    return crud.render_details(
        request,
        RESOURCE,
        chapter,
        {"report": report, "problem": problem},
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.add_chapter", raise_exception=True)
def create(request: AppRequest) -> HttpResponse:
    return crud.render_form(request, RESOURCE, save=_save)


@require_http_methods(["GET", "POST"])
@permission_required("app.change_chapter", raise_exception=True)
def update(request: AppRequest, pk: int) -> HttpResponse:
    chapter = get_object_or_404(Chapter, pk=pk)

    return crud.render_form(request, RESOURCE, instance=chapter, save=_save)


@require_http_methods(["GET", "POST"])
@permission_required("app.delete_chapter", raise_exception=True)
def delete(request: AppRequest, pk: int) -> HttpResponse:
    chapter = get_object_or_404(Chapter, pk=pk)

    return crud.render_delete(
        request,
        RESOURCE,
        [chapter.pk],
        delete=Chapter.objects.delete_many,
        names=[chapter.name],
    )


@require_POST
@permission_required("app.delete_chapter", raise_exception=True)
def bulk_delete(request: AppRequest) -> HttpResponse:
    ids = crud.selected_ids(request)

    names = Chapter.objects.filter(pk__in=ids).values_list("name", flat=True)

    return crud.render_delete(
        request, RESOURCE, ids, delete=Chapter.objects.delete_many, names=names
    )


@require_POST
def select(request: AppRequest) -> HttpResponse:
    """The header's chapter switcher: every page now shows this chapter."""
    chapter = get_object_or_404(Chapter, pk=request.POST.get("chapter") or 0)

    request.session[SESSION_CHAPTER] = chapter.pk

    target = request.POST.get("next", "/")

    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "/"

    return redirect(target)


@require_POST
@permission_required("app.change_chapter", raise_exception=True)
def set_default(request: AppRequest, pk: int) -> HttpResponse:
    chapter = get_object_or_404(Chapter, pk=pk)

    Chapter.objects.set_default(chapter)

    messages.success(request, _("%(name)s is the default chapter now.") % {"name": chapter})

    return crud.trigger(HttpResponse(""), refresh=True)


@require_http_methods(["GET", "POST"])
@permission_required("app.add_chapter", raise_exception=True)
def duplicate(request: AppRequest, pk: int) -> HttpResponse:
    """Copy a chapter with all of its data (to try another scenario) and switch to it."""
    chapter = get_object_or_404(Chapter, pk=pk)

    form = forms.DuplicateChapterForm(
        request.POST or None,
        initial={"name": _("%(name)s (copy)") % {"name": chapter.name}},
    )

    if request.method == "POST" and form.is_valid():
        try:
            copy = Chapter.objects.duplicate(chapter, form.cleaned_data["name"])
        except (DomainError, UserError) as error:
            form.add_error(None, error_text(error))
        else:
            request.session[SESSION_CHAPTER] = copy.pk
            messages.success(
                request, _("%(name)s created: it is the chapter shown now.") % {"name": copy}
            )
            response = HttpResponse("")
            response["HX-Refresh"] = "true"
            return response

    context = {
        "form": form,
        "chapter": chapter,
        "action_url": request.path,
        "page_title": _("duplicate %(name)s") % {"name": chapter.name},
    }

    return render(request, "app/chapters/duplicate-modal.html", context)


def _save(form: forms.ChapterForm) -> Chapter:
    return Chapter.objects.save_chapter(form.save(commit=False))


@require_POST
@permission_required("app.change_chapter", raise_exception=True)
def bulk_edit(request: AppRequest) -> HttpResponse:
    return crud.render_bulk_edit(
        request,
        RESOURCE,
        crud.selected_ids(request),
        update=Chapter.objects.bulk_set,
    )


@require_POST
@permission_required("app.change_chapter", raise_exception=True)
def bulk_action(request: AppRequest) -> HttpResponse:
    ids = crud.selected_ids(request)

    return crud.render_bulk_action(
        request,
        RESOURCE,
        ids,
        run=lambda action, ids: Chapter.objects.bulk_set(ids, dict(action.values)),
        names=Chapter.objects.filter(pk__in=ids).values_list("name", flat=True),
    )
