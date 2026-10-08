from typing import Any

import django_filters as filters
from django import forms
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..choices import (
    ContractTypeChoices,
    DegreeChoices,
    EmploymentTypeChoices,
    SpecializationTypeChoices,
)
from ..models import Contract, Faculty, Specialization
from .base import BaseFilterSet, boolean_choice, yes_no_choice


class ContractFilter(BaseFilterSet):
    faculty = filters.ModelMultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("faculty"),
        queryset=Faculty.objects.none(),
    )
    signed = yes_no_choice(
        _("signed"), yes=_("signed to a faculty"), no=_("unsigned"), method="filter_signed"
    )
    specialization = filters.ModelMultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("specialization"),
        field_name="employee__specialization",
        queryset=Specialization.objects.none(),
    )
    specialization_type = filters.MultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("specialization type"),
        choices=SpecializationTypeChoices.choices,
    )
    degree = filters.MultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("degree"),
        choices=DegreeChoices.choices,
    )
    contract_type = filters.MultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("contract type"),
        choices=ContractTypeChoices.choices,
    )
    employment_type = filters.MultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("employment type"),
        choices=EmploymentTypeChoices.choices,
    )
    is_active = boolean_choice(_("is active"), yes=_("on"), no=_("off"), field_name="is_active")
    is_locked = boolean_choice(
        _("locked to its faculty"), yes=_("locked"), no=_("not locked"), field_name="is_locked"
    )

    class Meta:
        model = Contract
        fields = ("q",)

    def __init__(self, *args: Any, request: HttpRequest | None = None, **kwargs: Any) -> None:
        super().__init__(*args, request=request, **kwargs)

        chapter = getattr(request, "chapter", None)

        for name, model in (("faculty", Faculty), ("specialization", Specialization)):
            queryset = model.objects.filter(chapter=chapter)
            self.filters[name].queryset = queryset
            self.form.fields[name].queryset = queryset

    def filter_signed(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        return queryset.filter(faculty__isnull=value != "1")
