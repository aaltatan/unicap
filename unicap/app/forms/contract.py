from typing import Any, cast

from django import forms
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

from ..models import Contract, Employee
from .base import ChapterOwnedForm


class ContractForm(ChapterOwnedForm):
    """An employee has one contract per chapter: only employees without one are offered."""

    chapter_querysets = ("employee", "faculty")

    class Meta:
        model = Contract
        fields = (
            "employee",
            "faculty",
            "degree",
            "contract_type",
            "employment_type",
            "is_active",
            "notes",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 2, "x-autosize": ""})}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        employees = cast("forms.ModelChoiceField", self.fields["employee"])
        employees.queryset = (
            cast("QuerySet", employees.queryset)
            .filter(
                Q(contract__isnull=True) | Q(pk=self.instance.employee_id),
            )
            .select_related("specialization")
        )
        employees.label_from_instance = _employee_label  # type: ignore[method-assign, assignment]  # Django's documented hook

        cast("forms.ModelChoiceField", self.fields["faculty"]).empty_label = _("unsigned")
        self.fields["faculty"].help_text = _("empty: unsigned (placed on the board later)")


def _employee_label(employee: Employee) -> str:
    """`name · specialization` in the employee select."""
    return f"{employee.name} · {employee.specialization.name}"
