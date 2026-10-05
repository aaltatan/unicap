from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Employee
from .base import ChapterOwnedForm


class EmployeeForm(ChapterOwnedForm):
    chapter_querysets = ("specialization", "excluded_faculties")

    class Meta:
        model = Employee
        fields = ("name", "specialization", "is_active", "excluded_faculties", "notes")
        widgets = {
            "excluded_faculties": forms.CheckboxSelectMultiple,
            "name": forms.TextInput(attrs={"placeholder": _("e.g. Dr. Sami"), "autofocus": True}),
            "notes": forms.Textarea(attrs={"rows": 2, "x-autosize": ""}),
        }
