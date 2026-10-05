from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

from django.db.models import Max
from django.utils.translation import gettext as _

from unicap.domain import ContractStatus

from ..exceptions import UserError
from ..querysets import ContractQuerySet
from .base import ChapterOwnedManager, chapters, check_rows

if TYPE_CHECKING:
    from ..models import Contract


class ContractManager(ChapterOwnedManager.from_queryset(ContractQuerySet)):  # type: ignore[misc]
    """Contracts: a new or re-signed contract is signed last (its `position`)."""

    def save_contract(self, contract: "Contract") -> "Contract":
        """Save a contract in its employee's chapter; re-signing puts it last.

        Raises:
            DomainError: the chapter would break a domain rule; nothing is saved.
        """
        contract.chapter_id = contract.employee.chapter_id

        previous = self.filter(pk=contract.pk).values_list("faculty_id", flat=True).first()

        with chapters().validated(contract.chapter_id):
            if contract.pk is None or previous != contract.faculty_id:
                contract.position = chapters().next_position(contract.chapter)

            contract.save()

        return contract

    def bulk_set(self, chapter_id: int, ids: Iterable[int], values: Mapping[str, Any]) -> int:
        """Set `values` on several contracts; the ones signed to a new faculty go last.

        Raises:
            DomainError: the chapter would break a domain rule; nothing is saved.
        """
        with chapters().validated(chapter_id):
            rows = self.filter(chapter_id=chapter_id, pk__in=list(ids))
            check_rows(rows, values)

            if "faculty" in values:
                faculty = values["faculty"]
                moved = rows.exclude(faculty=faculty).order_by("position", "pk")
                last = self.filter(chapter_id=chapter_id).aggregate(last=Max("position"))["last"]

                for position, contract in enumerate(moved, start=(last or 0) + 1):
                    contract.position = position
                    contract.save(update_fields=("position",))

            return rows.update(**values)

    def move(self, contract: "Contract", faculty_id: int | None) -> "Contract":
        """Drag and drop: sign the contract to `faculty_id` (None: unsigned).

        Raises:
            UserError: there is no such faculty; nothing is saved.
            DomainError: the faculty is not the chapter's; nothing is saved.
        """
        faculties = self.model._meta.get_field("faculty").related_model._default_manager  # noqa: SLF001

        if faculty_id is not None and not faculties.filter(pk=faculty_id).exists():
            raise UserError(_("this faculty is not there any more."))

        contract.faculty_id = faculty_id

        return self.save_contract(contract)

    def attach_statuses(self, contracts: Iterable["Contract"], chapter_id: int) -> list["Contract"]:
        """Set `status` (a `ContractStatus`, None when unsigned) on each contract row.

        The status comes from evaluating the whole chapter with the domain.
        """
        snapshot = chapters().get_snapshot(chapter_id)

        report = snapshot.report()

        rows = list(contracts)

        for row in rows:
            employee = snapshot.employees.get(row.employee_id)

            row.status = report.status_of(employee) if employee else None
            row.is_counted = row.status is ContractStatus.COUNTED

        return rows
