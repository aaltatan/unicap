"""Shared filter building blocks: the search box and number ranges."""

from typing import TYPE_CHECKING, cast

import django_filters as filters
from django import forms
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from ..utils import StrOrPromise

if TYPE_CHECKING:
    from ..querysets.base import BaseQuerySet


class BaseFilterSet(filters.FilterSet):
    """Every table's filters: `q` searches (keywords or DjangoQL), the rest narrow down.

    `q` is typed in the table's search box; the other fields fill the filters sidebar.
    """

    q = filters.CharFilter(
        method="filter_search",
        label=_("search"),
        widget=forms.TextInput(attrs={"placeholder": _("search"), "type": "search"}),
    )

    def filter_search(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        """Keywords or a DjangoQL query: `BaseQuerySet.search`."""
        return cast("BaseQuerySet", queryset).search(value)


def number_range(
    field_name: str, label: StrOrPromise
) -> tuple[filters.NumberFilter, filters.NumberFilter]:
    """Two filters, `from` (>=) and `to` (<=), for one numeric field.

    Example:
        >>> students_from, students_to = number_range("max_students", "max students")
    """
    return (
        filters.NumberFilter(
            field_name=field_name,
            lookup_expr="gte",
            label=label,
            widget=forms.NumberInput(attrs={"placeholder": _("from")}),
        ),
        filters.NumberFilter(
            field_name=field_name,
            lookup_expr="lte",
            label=label,
            widget=forms.NumberInput(attrs={"placeholder": _("to")}),
        ),
    )


def boolean_choice(
    label: StrOrPromise, *, yes: StrOrPromise, no: StrOrPromise, field_name: str
) -> filters.ChoiceFilter:
    """A yes / no / any select for a boolean field."""
    return filters.ChoiceFilter(
        field_name=field_name,
        label=label,
        choices=(("1", yes), ("0", no)),
        empty_label=_("any"),
        method=_filter_boolean,
    )


def yes_no_choice(
    label: StrOrPromise, *, yes: StrOrPromise, no: StrOrPromise, method: str
) -> filters.ChoiceFilter:
    """A yes / no / any select handled by a filter method (it receives `"1"` or `"0"`)."""
    return filters.ChoiceFilter(
        label=label,
        choices=(("1", yes), ("0", no)),
        empty_label=_("any"),
        method=method,
    )


def _filter_boolean(queryset: QuerySet, name: str, value: str) -> QuerySet:
    return queryset.filter(**{name: value == "1"})
