from typing import Any

import django_filters as filters
from django import forms
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..choices import SpecializationTypeChoices
from ..models import Employee, Faculty, Specialization
from .base import BaseFilterSet, boolean_choice, yes_no_choice


class EmployeeFilter(BaseFilterSet):
    specialization = filters.ModelMultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("specialization"),
        queryset=Specialization.objects.none(),
    )
    specialization_type = filters.MultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("specialization type"),
        choices=SpecializationTypeChoices.choices,
    )
    faculty = filters.ModelMultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("faculty"),
        field_name="contract__faculty",
        queryset=Faculty.objects.none(),
    )
    is_active = boolean_choice(
        _("is active"), yes=_("active"), no=_("inactive"), field_name="is_active"
    )
    has_contract = yes_no_choice(
        _("contract"), yes=_("has a contract"), no=_("no contract"), method="filter_has_contract"
    )

    class Meta:
        model = Employee
        fields = ("q",)

    def __init__(self, *args: Any, request: HttpRequest | None = None, **kwargs: Any) -> None:
        super().__init__(*args, request=request, **kwargs)

        chapter = getattr(request, "chapter", None)

        for name, model in (("specialization", Specialization), ("faculty", Faculty)):
            queryset = model.objects.filter(chapter=chapter)
            self.filters[name].queryset = queryset
            self.form.fields[name].queryset = queryset

    def filter_has_contract(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        return queryset.filter(contract__isnull=value != "1")
