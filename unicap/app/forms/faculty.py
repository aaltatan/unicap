from typing import Any, cast

from django import forms
from django.db import models
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from ..choices import ContractTypeChoices
from ..models import Faculty, FacultySpecialization, Specialization
from ..models.faculty_specialization import DEFAULT_MASTERS_PER_PHD
from ..widgets import NumberInput
from .base import ChapterOwnedForm


class FacultyForm(ChapterOwnedForm):
    class Meta:
        model = Faculty
        fields = (
            "name",
            "students_per_phd",
            "min_staff_percentage",
            "current_students",
            "target_students",
            "max_students",
            "min_specialized",
            "max_specialized",
            "min_supported",
            "max_supported",
            "staff_rounding",
            "masters_rounding",
            "max_share_rounding",
            "min_share_rounding",
            "notes",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("e.g. Dentistry"), "autofocus": True}),
            "min_staff_percentage": NumberInput(),
            "notes": forms.Textarea(attrs={"rows": 2, "x-autosize": ""}),
        }

    def clean_name(self) -> str:
        name = self.cleaned_data["name"].strip()

        taken = Faculty.objects.filter(chapter=self.instance.chapter_id, name=name)

        if taken.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("this chapter already has a faculty with this name."))

        return name


class ShareForm(forms.ModelForm):
    """One accepted specialization of the faculty, with its share and teacher bounds."""

    contract_type = forms.ChoiceField(
        label=_("contract type"),
        choices=[("", _("any")), *ContractTypeChoices.choices],
        required=False,
    )

    class Meta:
        model = FacultySpecialization
        fields = (
            "specialization",
            "specialization_type",
            "percentage",
            "min_percentage",
            "max_percentage",
            "min_teachers",
            "max_teachers",
            "contract_type",
            "calculate_masters",
            "masters_per_phd",
            "position",
        )
        widgets = {
            "position": forms.HiddenInput(),
            "percentage": NumberInput(attrs={"placeholder": "%"}),
            "min_percentage": NumberInput(attrs={"placeholder": "%"}),
            "max_percentage": NumberInput(attrs={"placeholder": "%"}),
            "min_teachers": forms.NumberInput(attrs={"placeholder": _("min")}),
            "max_teachers": forms.NumberInput(attrs={"placeholder": _("max")}),
            "masters_per_phd": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["masters_per_phd"].required = False

    def clean_masters_per_phd(self) -> int:
        """Empty: the usual two masters a PhD."""
        value = self.cleaned_data.get("masters_per_phd")

        return DEFAULT_MASTERS_PER_PHD if value is None else value


class SharesFormSet(forms.BaseInlineFormSet):
    """The faculty's accepted specializations: each once, chosen from its chapter."""

    def __init__(self, *args: Any, chapter: models.Model | None = None, **kwargs: Any) -> None:
        self.specializations = Specialization.objects.filter(chapter=chapter).order_by("name")
        self._choices: list[tuple[object, str]] | None = None

        super().__init__(*args, **kwargs)

    @property
    def specialization_choices(self) -> list[tuple[object, str]]:
        """The select's options, read once for every row (each row would query them again)."""
        if self._choices is None:
            self._choices = [
                ("", "---------"),
                *((row.pk, str(row)) for row in self.specializations),
            ]

        return self._choices

    def _construct_form(self, i: int, **kwargs: Any) -> forms.BaseForm:
        return self._limited(super()._construct_form(i, **kwargs))  # type: ignore[misc]  # Django's, not in the stubs

    @property
    def empty_form(self) -> forms.BaseForm:  # type: ignore[override]  # narrowed by _limited
        return self._limited(super().empty_form)

    def _limited(self, form: forms.BaseForm) -> forms.BaseForm:
        """Only the chapter's specializations; the position follows the rows' order."""
        field = cast("forms.ModelChoiceField", form.fields["specialization"])
        field.queryset = self.specializations  # what a posted value is checked against
        field.choices = self.specialization_choices
        form.fields["position"].required = False
        return form

    def clean(self) -> None:
        super().clean()

        chosen = [
            form.cleaned_data["specialization"]
            for form in self.forms
            if form.cleaned_data.get("specialization") and not form.cleaned_data.get("DELETE")
        ]

        if repeated := sorted({s.name for s in chosen if chosen.count(s) > 1}):
            raise forms.ValidationError(
                _("each specialization is accepted once: %(names)s")
                % {"names": ", ".join(repeated)},
            )


shares_formset = inlineformset_factory(
    Faculty,
    FacultySpecialization,
    form=ShareForm,
    formset=SharesFormSet,
    extra=0,
    can_delete=True,
)
