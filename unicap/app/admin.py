"""The admin panel (superusers only): every model, the settings and the report templates.

Writes to a chapter's data are checked like in the app: after saving or deleting, the whole
chapter must still be valid, else everything is rolled back and the reason is shown.
"""

from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from django.db.models import Model, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from solo.admin import SingletonModelAdmin

from unicap.domain import DomainError

from .choices import ReportChoices
from .exceptions import UserError
from .models import (
    AppSettings,
    Backup,
    Chapter,
    ChapterSettings,
    Contract,
    ContractSettings,
    Employee,
    EmployeeSettings,
    Faculty,
    FacultySettings,
    FacultySpecialization,
    ReportTemplate,
    Specialization,
    SpecializationSettings,
    User,
)
from .reports import VARIABLES
from .texts import error_text

admin.site.register(User, UserAdmin)

for singleton in (
    AppSettings,
    ChapterSettings,
    SpecializationSettings,
    FacultySettings,
    EmployeeSettings,
    ContractSettings,
):
    admin.site.register(singleton, SingletonModelAdmin)


class ValidatedAdmin(admin.ModelAdmin):
    """Saves and deletes that leave a chapter invalid are refused, with the reason."""

    def chapter_ids(self, objects: Iterable[Model]) -> set[int]:
        """The chapters the written rows belong to."""
        return {getattr(obj, "chapter_id") for obj in objects}  # noqa: B009 - owned rows

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:  # noqa: FBT001
        super().save_related(request, form, formsets, change)
        _validate(self.chapter_ids([form.instance]))

    def delete_model(self, request: HttpRequest, obj: Model) -> None:
        chapters = self.chapter_ids([obj])
        super().delete_model(request, obj)
        _validate(chapters)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet) -> None:
        with transaction.atomic():
            chapters = self.chapter_ids(queryset)
            super().delete_queryset(request, queryset)
            _validate(chapters)

    def changeform_view(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self._refusing(request, super().changeform_view, *args, **kwargs)

    def delete_view(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self._refusing(request, super().delete_view, *args, **kwargs)

    def changelist_view(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return self._refusing(request, super().changelist_view, *args, **kwargs)

    def _refusing(self, request: HttpRequest, view: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        """Run an admin view (one transaction); a broken rule rolls it back and is shown."""
        try:
            return view(request, *args, **kwargs)
        except (DomainError, UserError) as error:
            self.message_user(request, error_text(error), messages.ERROR)
            return HttpResponseRedirect(request.get_full_path())


@admin.register(Chapter)
class ChapterAdmin(ValidatedAdmin):
    list_display = (
        "name",
        "max_students",
        "is_default",
        "created_at",
    )
    list_filter = ("is_default",)
    search_fields = ("name", "notes")

    def chapter_ids(self, objects: Iterable[Model]) -> set[int]:
        return {obj.pk for obj in objects}

    def save_model(self, request: HttpRequest, obj: Chapter, form: Any, change: bool) -> None:  # noqa: FBT001
        Chapter.objects.save_chapter(obj)

    def delete_model(self, request: HttpRequest, obj: Model) -> None:
        admin.ModelAdmin.delete_model(self, request, obj)  # nothing left to validate

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet) -> None:
        admin.ModelAdmin.delete_queryset(self, request, queryset)


@admin.register(Specialization)
class SpecializationAdmin(ValidatedAdmin):
    list_display = ("name", "chapter", "is_active")
    list_filter = ("chapter", "is_active")
    search_fields = ("name", "notes")


class ShareInline(admin.TabularInline):
    model = FacultySpecialization
    extra = 0
    ordering = ("position",)


@admin.register(Faculty)
class FacultyAdmin(ValidatedAdmin):
    list_display = ("name", "chapter", "students_per_phd", "min_staff_percentage", "max_students")
    list_filter = ("chapter",)
    search_fields = ("name", "notes")
    inlines = (ShareInline,)


@admin.register(Employee)
class EmployeeAdmin(ValidatedAdmin):
    list_display = ("name", "chapter", "specialization", "is_active")
    list_filter = ("chapter", "is_active")
    search_fields = ("name", "notes")
    autocomplete_fields = ("specialization",)


@admin.register(Contract)
class ContractAdmin(ValidatedAdmin):
    list_display = (
        "employee",
        "chapter",
        "faculty",
        "degree",
        "contract_type",
        "employment_type",
        "is_active",
        "position",
    )
    list_filter = ("chapter", "degree", "contract_type", "employment_type", "is_active")
    search_fields = ("employee__name", "faculty__name", "notes")
    autocomplete_fields = ("employee", "faculty")


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """The saved backups, to look at and clean up (they are taken and restored in the app)."""

    list_display = ("created_at", "scope", "section", "chapter_name", "size", "created_by")
    list_filter = ("scope", "section")
    search_fields = ("chapter_name", "notes")
    readonly_fields = (
        "scope",
        "section",
        "chapter",
        "chapter_name",
        "download",
        "size",
        "created_at",
        "created_by",
    )
    exclude = ("file",)  # kept out of the served media: it has no address of its own

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @admin.display(description=_("file"))
    def download(self, obj: Backup) -> str:
        """The backup's file, through the app's download page."""
        return format_html('<a href="{}">{}</a>', obj.get_download_url(), obj.file.name)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    """Upload a report's Word template: start from the built-in one, see the variables."""

    list_display = ("report", "language", "file", "updated_at")
    list_filter = ("report", "language")
    fields = ("report", "language", "file", "notes", "built_in", "variables")
    readonly_fields = ("built_in", "variables")

    @admin.display(description=_("built-in templates"))
    def built_in(self, obj: ReportTemplate | None) -> str:
        """Download links: the built-in template of every report and language."""
        links = [
            (
                reverse("reports:default-template", args=(report, language)),
                f"{report.label} ({name})",
            )
            for report in ReportChoices
            for language, name in settings.LANGUAGES
        ]
        return format_html_join(format_html("<br>"), '<a href="{}">{}</a>', links)

    @admin.display(description=_("variables"))
    def variables(self, obj: ReportTemplate | None) -> str:
        """What each report's template can show."""
        return format_html_join(
            "",
            '<p><b>{}</b></p><pre style="white-space: pre-wrap">{}</pre>',
            ((report.label, VARIABLES[report]) for report in ReportChoices),
        )


def _validate(chapter_ids: Iterable[int]) -> None:
    """Every chapter must still be valid (a chapter deleted meanwhile is skipped).

    Raises:
        DomainError: a chapter breaks a domain rule.
    """
    for chapter_id in chapter_ids:
        if Chapter.objects.filter(pk=chapter_id).exists():
            with Chapter.objects.validated(chapter_id):
                pass
