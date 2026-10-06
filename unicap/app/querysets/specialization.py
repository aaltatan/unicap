from typing import Self

from django.db.models import Count

from ..constants import specialization as constants
from .base import BaseQuerySet


class SpecializationQuerySet(BaseQuerySet):
    """Specializations: how much each one is used."""

    search_fields = constants.SEARCH_FIELDS

    def annotate_usage(self) -> Self:
        """How many faculties accept each specialization, and how many employees hold it."""
        return self.annotate(
            faculties_count=Count("shares", distinct=True),
            employees_count=Count("employees", distinct=True),
        )
