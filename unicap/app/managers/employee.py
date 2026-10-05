from collections.abc import Iterable
from typing import TYPE_CHECKING

from ..querysets import EmployeeQuerySet
from .base import ChapterOwnedManager, chapters

if TYPE_CHECKING:
    from ..models import Employee


class EmployeeManager(ChapterOwnedManager.from_queryset(EmployeeQuerySet)):  # type: ignore[misc]
    """Employees: one with a contract cannot be deleted (delete the contract first)."""

    def attach_statuses(self, employees: Iterable["Employee"], chapter_id: int) -> list["Employee"]:
        """Set `status` (their contract's `ContractStatus`; None: unsigned or no contract)."""
        snapshot = chapters().get_snapshot(chapter_id)

        report = snapshot.report()

        rows = list(employees)

        for row in rows:
            employee = snapshot.employees.get(row.pk)
            row.status = report.status_of(employee) if employee else None

        return rows
