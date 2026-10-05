from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from ..models import Specialization
from .base import BaseFilterSet, boolean_choice, yes_no_choice


class SpecializationFilter(BaseFilterSet):
    is_active = boolean_choice(
        _("is active"), yes=_("active"), no=_("inactive"), field_name="is_active"
    )
    used = yes_no_choice(
        _("used"), yes=_("used by a faculty or employee"), no=_("unused"), method="filter_used"
    )

    class Meta:
        model = Specialization
        fields = ("q",)

    def filter_used(self, queryset: QuerySet, name: str, value: str) -> QuerySet:  # noqa: ARG002
        used = queryset.filter(shares__isnull=False) | queryset.filter(employees__isnull=False)

        return used.distinct() if value == "1" else queryset.exclude(pk__in=used.values("pk"))
