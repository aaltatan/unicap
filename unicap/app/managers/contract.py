from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

from django.db.models import Max
from django.utils.translation import gettext as _

from unicap.domain import ContractStatus

from ..choices import ContractTypeChoices, DegreeChoices, EmploymentTypeChoices
from ..exceptions import UserError
from ..querysets import ContractQuerySet
from .base import ChapterOwnedManager, chapters, check_rows

if TYPE_CHECKING:
    from ..models import Contract


class ContractManager(ChapterOwnedManager.from_queryset(ContractQuerySet)):  # type: ignore[misc]
    """Contracts: a new or re-signed contract is signed last (its `position`).

    A locked contract stays in the faculty it is signed to: every write that would move
    it is refused (unlock it first, or in the same save).
    """

    def save_contract(self, contract: "Contract") -> "Contract":
        """Save a contract in its employee's chapter; re-signing puts it last.

        Raises:
            UserError: the contract is locked to another faculty; nothing is saved.
            DomainError: the chapter would break a domain rule; nothing is saved.
        """
        contract.chapter_id = contract.employee.chapter_id

        stored = self.filter(pk=contract.pk)

        previous = stored.values_list("faculty_id", flat=True).first()

        if contract.is_locked:  # saved unlocked, it may move in the same save
            self.check_movable(stored, contract.faculty_id)

        with chapters().validated(contract.chapter_id):
            if contract.pk is None or previous != contract.faculty_id:
                contract.position = chapters().next_position(contract.chapter)

            contract.save()

        return contract

    def bulk_set(self, chapter_id: int, ids: Iterable[int], values: Mapping[str, Any]) -> int:
        """Set `values` on several contracts; the ones signed to a new faculty go last.

        Raises:
            UserError: a contract is locked to another faculty; nothing is saved.
            DomainError: the chapter would break a domain rule; nothing is saved.
        """
        with chapters().validated(chapter_id):
            rows = self.filter(chapter_id=chapter_id, pk__in=list(ids))
            check_rows(rows, values)

            if "faculty" in values:
                faculty = values["faculty"]

                if values.get("is_locked", True):  # unlocked here, they may move
                    self.check_movable(rows, faculty.pk if faculty else None)

                moved = rows.exclude(faculty=faculty).order_by("position", "pk")
                last = self.filter(chapter_id=chapter_id).aggregate(last=Max("position"))["last"]

                for position, contract in enumerate(moved, start=(last or 0) + 1):
                    contract.position = position
                    contract.save(update_fields=("position",))

            return rows.update(**values)

    def move(self, contract: "Contract", faculty_id: int | None) -> "Contract":
        """Drag and drop: sign the contract to `faculty_id` (None: unsigned).

        Raises:
            UserError: there is no such faculty, or the contract is locked to another one;
                nothing is saved.
            DomainError: the faculty is not the chapter's; nothing is saved.
        """
        faculties = self.model._meta.get_field("faculty").related_model._default_manager  # noqa: SLF001

        if faculty_id is not None and not faculties.filter(pk=faculty_id).exists():
            raise UserError(_("this faculty is not there any more."))

        contract.faculty_id = faculty_id

        return self.save_contract(contract)

    def switch(self, contract: "Contract", field: str) -> "Contract":
        """Switch one of the contract's two-valued terms to its other value.

        `is_active`, `is_locked`, `degree` (PhD / master), `contract_type` (fulltime /
        parttime) or `employment_type` (staff / borrowed).

        Raises:
            UserError: `field` is not one of them.
            DomainError: the contract or its chapter would break a domain rule (a parttime
                contract is always borrowed); nothing is saved.

        Example:
            ```python
            Contract.objects.switch(contract, "employment_type")  # staff -> borrowed
            ```
        """
        if field not in SWITCHES:
            msg = _("%(field)s cannot be switched: %(fields)s") % {
                "field": field,
                "fields": ", ".join(SWITCHES),
            }
            raise UserError(msg)

        current = getattr(contract, field)

        setattr(contract, field, next(value for value in SWITCHES[field] if value != current))

        contract.to_domain()  # the contract's own rule first, with its own message

        return self.save_contract(contract)

    def check_movable(self, rows: ContractQuerySet, faculty_id: int | None) -> None:
        """Refuse to sign `rows` to `faculty_id` (None: unsigned) when one is locked elsewhere.

        Raises:
            UserError: naming the locked contracts and the faculties they stay in.
        """
        _refuse(rows.pinned().moving_to(faculty_id))

    def check_placements(self, placements: Mapping[int, int | None]) -> None:
        """Refuse `placements` (contract id -> faculty id) that move a locked contract.

        Raises:
            UserError: naming the locked contracts and the faculties they stay in.
        """
        rows = self.filter(pk__in=list(placements))

        moving = [
            pk
            for pk, faculty_id in rows.pinned().values_list("pk", "faculty_id")
            if placements.get(pk, faculty_id) != faculty_id
        ]

        _refuse(rows.filter(pk__in=moving))

    def by_employee(self, chapter_id: int, faculty_id: int) -> dict[int, "Contract"]:
        """A faculty's contract rows by employee id, their employee and specialization selected.

        A domain contract's employee id is its employee row's: this leads a report's staff
        back to their rows (and so to their pages).
        """
        rows = self.for_chapter(chapter_id).filter(faculty_id=faculty_id).with_relations()

        return {row.employee_id: row for row in rows}

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


# a contract's two-valued terms, each with its two values
SWITCHES: dict[str, tuple[object, ...]] = {
    "is_active": (True, False),
    "is_locked": (True, False),
    "degree": tuple(DegreeChoices.values),
    "contract_type": tuple(ContractTypeChoices.values),
    "employment_type": tuple(EmploymentTypeChoices.values),
}


def _refuse(pinned: ContractQuerySet) -> None:
    """Raise a `UserError` naming the locked contracts a write would move (none: nothing)."""
    rows = pinned.select_related("employee", "faculty")[:10]

    if names := [f"{row.employee.name} ({row.faculty.name})" for row in rows]:
        msg = _("locked to their faculty (unlock them first): %(names)s") % {
            "names": _(", ").join(names),
        }
        raise UserError(msg)
