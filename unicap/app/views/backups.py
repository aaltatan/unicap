"""Backups: take them (everything, a chapter, a section), download, upload and restore them."""

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from unicap.domain import DomainError

from .. import forms
from ..backups import service
from ..choices import BackupScopeChoices, BackupSectionChoices
from ..exceptions import UserError
from ..models import Backup, Chapter
from ..requests import AppRequest
from ..texts import error_text


@require_GET
@permission_required("app.view_backup", raise_exception=True)
def index(request: AppRequest) -> HttpResponse:
    scope = request.GET.get("scope", "")
    section = request.GET.get("section", "")
    chapter = request.GET.get("chapter", "")

    backups = Backup.objects.for_listing(
        scope=scope if scope in BackupScopeChoices.values else "",
        section=section if section in BackupSectionChoices.values else "",
        chapter_id=int(chapter) if chapter.isdigit() else None,
    )

    return render(
        request,
        "app/backups/index.html",
        {
            "page_title": _("backups"),
            "backups": backups,
            "scopes": BackupScopeChoices.choices,
            "sections": BackupSectionChoices.choices,
            "chapters": Chapter.objects.only("pk", "name"),
            "filters": {"scope": scope, "section": section, "chapter": chapter},
            "can_add": request.user.has_perm("app.add_backup"),
            "can_restore": request.user.has_perm("app.restore_backup"),
            "can_delete": request.user.has_perm("app.delete_backup"),
        },
    )


@require_POST
@permission_required("app.add_backup", raise_exception=True)
def create(request: AppRequest) -> HttpResponse:
    """Take a backup, then go back where it was asked from (`next`), or to the backups."""
    form = forms.CreateBackupForm(request.POST)

    if not form.is_valid():
        messages.error(request, _("this backup cannot be taken."))
        return _back(request)

    data = form.cleaned_data

    try:
        backup = service.create(
            data["scope"],
            chapter=data["chapter"] or getattr(request, "chapter", None),
            section=data["section"],
            user=request.user,
            notes=data["notes"],
        )
    except UserError as error:
        messages.error(request, error_text(error))
    else:
        messages.success(request, _("backup saved: %(backup)s") % {"backup": backup})

    return _back(request)


@require_http_methods(["GET", "POST"])
@permission_required("app.add_backup", raise_exception=True)
def upload(request: AppRequest) -> HttpResponse:
    form = forms.UploadBackupForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        try:
            backup = service.upload(
                form.cleaned_data["file"],
                user=request.user,
                notes=form.cleaned_data["notes"],
            )
        except UserError as error:
            form.add_error("file", error_text(error))
        else:
            messages.success(request, _("backup uploaded: %(backup)s") % {"backup": backup})
            return _redirect(reverse("backups:index"))

    return render(request, "app/backups/upload-modal.html", {"form": form})


@require_http_methods(["GET", "POST"])
@permission_required("app.restore_backup", raise_exception=True)
def restore(request: AppRequest, pk: int) -> HttpResponse:
    backup = get_object_or_404(Backup, pk=pk)

    # bound on every POST: a system backup's form has no fields, so its POST body is empty
    data = request.POST if request.method == "POST" else None

    form = forms.RestoreForm(data, backup=backup)

    if request.method == "POST" and form.is_valid():
        try:
            safety = service.restore(
                backup,
                chapter=form.cleaned_data.get("chapter"),
                new_chapter=form.cleaned_data.get("new_chapter", "").strip(),
                user=request.user,
            )
        except (DomainError, UserError) as error:
            form.add_error(None, error_text(error))
        else:
            messages.success(
                request,
                _("restored. What it replaced is saved as: %(backup)s") % {"backup": safety},
            )
            return _redirect(reverse("backups:index"))

    return render(request, "app/backups/restore-modal.html", {"backup": backup, "form": form})


@require_GET
@permission_required("app.view_backup", raise_exception=True)
def download(request: AppRequest, pk: int) -> FileResponse:  # noqa: ARG001
    backup = get_object_or_404(Backup, pk=pk)

    return FileResponse(
        backup.file.open("rb"),
        as_attachment=True,
        filename=(backup.file.name or "backup.json").rsplit("/", 1)[-1],
        content_type="application/json",
    )


@require_http_methods(["GET", "POST"])
@permission_required("app.delete_backup", raise_exception=True)
def delete(request: AppRequest, pk: int) -> HttpResponse:
    backup = get_object_or_404(Backup, pk=pk)

    if request.method == "POST":
        backup.delete()  # django-cleanup removes its file
        messages.success(request, _("backup deleted."))
        return _redirect(reverse("backups:index"))

    return render(request, "app/backups/delete-modal.html", {"backup": backup})


def _back(request: AppRequest) -> HttpResponse:
    """To `next` when it is a page of this site, else to the backups."""
    target = request.POST.get("next", "")

    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("backups:index")

    return redirect(target)


def _redirect(url: str) -> HttpResponse:
    """From a modal: reload the page at `url` (the data may have changed everywhere)."""
    response = HttpResponse("")
    response["HX-Redirect"] = url
    return response
