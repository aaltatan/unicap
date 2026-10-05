from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from ..choices import BackupScopeChoices, BackupSectionChoices
from ..models import Backup, Chapter


class CreateBackupForm(forms.Form):
    """What to back up: everything, a chapter, or a section of a chapter."""

    scope = forms.ChoiceField(choices=BackupScopeChoices.choices)
    section = forms.ChoiceField(choices=BackupSectionChoices.choices, required=False)
    chapter = forms.ModelChoiceField(queryset=Chapter.objects.all(), required=False)
    notes = forms.CharField(required=False, max_length=500)


class UploadBackupForm(forms.Form):
    file = forms.FileField(
        label=_("backup file"),
        widget=forms.ClearableFileInput(attrs={"accept": ".json,application/json"}),
        help_text=_("a .json file downloaded from the backups page"),
    )
    notes = forms.CharField(
        label=_("notes"),
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class RestoreForm(forms.Form):
    """Where a chapter or section backup goes: a chapter, or (a chapter backup) a new one."""

    chapter = forms.ModelChoiceField(
        label=_("restore into"),
        queryset=Chapter.objects.all(),
        required=False,
    )
    new_chapter = forms.CharField(
        label=_("or as a new chapter named"),
        required=False,
        max_length=255,
    )

    def __init__(self, *args: Any, backup: Backup, **kwargs: Any) -> None:
        """Default to the chapter the backup was taken from; only chapter backups make new ones."""
        super().__init__(*args, **kwargs)

        self.backup = backup
        self.fields["chapter"].initial = backup.chapter_id

        if backup.scope != BackupScopeChoices.CHAPTER:
            del self.fields["new_chapter"]

        if backup.scope == BackupScopeChoices.SYSTEM:
            del self.fields["chapter"]

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}

        needs_target = self.backup.scope != BackupScopeChoices.SYSTEM

        if needs_target and not data.get("chapter") and not data.get("new_chapter", "").strip():
            raise forms.ValidationError(_("choose a chapter, or name a new one."))

        return data
