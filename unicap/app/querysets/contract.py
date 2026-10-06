from typing import Self

from django.db.models import F, FilteredRelation, Q

from ..constants import contract as constants
from .base import BaseQuerySet


class ContractQuerySet(BaseQuerySet):
    """Contracts: signed or unsigned, with what their rows show."""

    search_fields = constants.SEARCH_FIELDS

    def with_relations(self) -> Self:
        """Select the employee, their specialization and the faculty in one query."""
        return self.select_related("employee", "employee__specialization", "faculty")

    def annotate_specialization_type(self) -> Self:
        """`specialization_type`: what the employee's specialization is in the contract's faculty.

        `specialized` or `supported` (the faculty's accepted specializations); None when the
        contract is unsigned, or its faculty does not accept the specialization.
        """
        return self.annotate(
            accepted=FilteredRelation(
                "faculty__shares",
                condition=Q(faculty__shares__specialization=F("employee__specialization")),
            ),
            specialization_type=F("accepted__specialization_type"),
        )

    def signed(self) -> Self:
        """Contracts signed to a faculty."""
        return self.filter(faculty__isnull=False)

    def unsigned(self) -> Self:
        """Contracts not signed to any faculty (the board's unsigned lane)."""
        return self.filter(faculty__isnull=True)
