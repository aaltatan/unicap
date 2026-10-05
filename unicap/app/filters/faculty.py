from typing import Any

import django_filters as filters
from django import forms
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..models import Faculty, Specialization
from .base import BaseFilterSet, number_range


class FacultyFilter(BaseFilterSet):
    accepts = filters.ModelMultipleChoiceFilter(
        widget=forms.CheckboxSelectMultiple,
        label=_("accepts"),
        field_name="shares__specialization",
        queryset=Specialization.objects.none(),
        distinct=True,
    )
    students_per_phd_from, students_per_phd_to = number_range(
        "students_per_phd", _("students per PhD")
    )
    max_students_from, max_students_to = number_range("max_students", _("max students"))
    current_students_from, current_students_to = number_range(
        "current_students", _("current students")
    )

    class Meta:
        model = Faculty
        fields = ("q",)

    def __init__(self, *args: Any, request: HttpRequest | None = None, **kwargs: Any) -> None:
        super().__init__(*args, request=request, **kwargs)

        chapter = getattr(request, "chapter", None)

        self.filters["accepts"].queryset = Specialization.objects.filter(chapter=chapter)
        self.form.fields["accepts"].queryset = self.filters["accepts"].queryset
