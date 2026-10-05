from django.db.models import F, FilteredRelation, Q
from typing_extensions import Self

from ..constants import employee as constants
from .base import BaseQuerySet


class EmployeeQuerySet(BaseQuerySet):
    """Employees: with or without their contract."""

    search_fields = constants.SEARCH_FIELDS

    def with_contract(self) -> Self:
        """Select the specialization and the contract (with its faculty) in one query."""
        return self.select_related("specialization", "contract", "contract__faculty")

    def annotate_specialization_type(self) -> Self:
        """`specialization_type`: what the employee's specialization is in their faculty.

        `specialized` or `supported`; None with no contract, an unsigned one, or a faculty
        that does not accept the specialization.
        """
        return self.annotate(
            accepted=FilteredRelation(
                "contract__faculty__shares",
                condition=Q(contract__faculty__shares__specialization=F("specialization")),
            ),
            specialization_type=F("accepted__specialization_type"),
        )

    def with_excluded_faculties(self) -> Self:
        """Prefetch the faculties each employee cannot be counted in (one query for all)."""
        return self.prefetch_related("excluded_faculties")

    def holding(self, specialization_id: int) -> Self:
        """Employees whose specialization this is."""
        return self.filter(specialization_id=specialization_id)

    def without_contract(self) -> Self:
        """Employees with no contract yet: an employee has at most one."""
        return self.filter(contract__isnull=True)
