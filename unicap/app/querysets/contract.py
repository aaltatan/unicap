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

    def pinned(self) -> Self:
        """Contracts that stay in their faculty: locked and signed (`Contract.is_pinned`)."""
        return self.filter(is_locked=True, faculty__isnull=False)

    def movable(self) -> Self:
        """Contracts that may be signed elsewhere or unsigned: every one that is not pinned."""
        return self.exclude(is_locked=True, faculty__isnull=False)

    def moving_to(self, faculty_id: int | None) -> Self:
        """Contracts that signing to `faculty_id` (None: unsigned) would take out of their place."""
        if faculty_id is None:
            return self.filter(faculty__isnull=False)

        return self.exclude(faculty_id=faculty_id)
