"""A chapter as the board sees it: the domain aggregate plus the row ids to write back."""

from collections.abc import Collection, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from django.utils.translation import gettext as _

from unicap.domain import (
    Chapter,
    ChapterFaculty,
    ChapterReport,
    Contract,
    ContractStatus,
    DomainError,
    Employee,
    Faculty,
    FacultyReport,
    HireKind,
    Outcome,
    Recommendation,
    RecommendationStrategy,
    Strategy,
    evaluate_chapter,
    in_staff_order,
    optimize,
    outcome_of,
    recommend,
    substitutes_for,
)

from .exceptions import UserError

DEFAULT_ROUNDS = 20


@dataclass(frozen=True)
class DropPreview:
    """What dropping a card on one lane would give (`faculty_id` None: the unsigned lane)."""

    faculty_id: int | None
    status: ContractStatus | None  # the contract's status there (None: unsigned)
    capacity: int  # the chapter's capacity after the drop


@dataclass(frozen=True)
class Card:
    """One contract on the board."""

    contract: Contract
    status: ContractStatus | None  # None: unsigned
    contract_id: int

    @property
    def employee_id(self) -> int:
        """The employee row id (the domain employee's id)."""
        return self.contract.employee.id

    @property
    def blocked_switches(self) -> tuple[str, ...]:
        """The two-valued terms the domain refuses to switch on this contract.

        `contract_type`, `employment_type` or `degree`, each tried with its other value
        (a fulltime staff contract cannot become parttime: parttime is always borrowed).
        """
        return tuple(
            name
            for name in ("degree", "contract_type", "employment_type")
            if not self._accepts(name, _other(getattr(self.contract, name)))
        )

    def _accepts(self, name: str, value: Enum) -> bool:
        changes: dict[str, Any] = {name: value}

        try:
            replace(self.contract, **changes)
        except DomainError:
            return False

        return True


@dataclass(frozen=True)
class Lane:
    """A board lane: the unsigned contracts (`faculty_id` None) or one faculty's."""

    faculty_id: int | None
    report: FacultyReport | None
    cards: tuple[Card, ...]

    @property
    def key(self) -> str:
        """`unsigned`, or the faculty row id: how the page names the lane."""
        return "unsigned" if self.faculty_id is None else str(self.faculty_id)


@dataclass(frozen=True)
class Substitute:
    """An employee whose contract could make a move in another's place."""

    employee: Employee
    contract_id: int


@dataclass(frozen=True)
class Move:
    """One contract the optimizer re-signs.

    `substitutes`: the employees who could move in this one's place, the same in everything
    a placement reads (the domain's `substitutes_for`) and not moved themselves.
    `chosen_id`: the contract that makes the move (the employee's own, or a substitute's).
    `is_removed`: the user took the move out: the employee stays where they are.
    """

    employee: Employee
    contract: Contract
    before: Faculty | None
    after: Faculty | None
    contract_id: int = 0
    substitutes: tuple[Substitute, ...] = ()
    chosen_id: int = 0
    is_removed: bool = False


@dataclass(frozen=True)
class Optimization:
    """A strategy's placement next to the current one. Nothing is saved.

    `after` and `after_outcome` are the chapter with the moves kept (not `is_removed`).
    """

    strategy: Strategy
    before: ChapterReport
    after: ChapterReport
    before_outcome: Outcome
    after_outcome: Outcome
    moves: tuple[Move, ...]
    placements: dict[int, int | None]  # contract id -> faculty id, to apply it

    @property
    def has_substitutes(self) -> bool:
        """Whether a move could be made by someone else."""
        return any(move.substitutes for move in self.moves)

    @property
    def kept(self) -> int:
        """How many moves would be applied."""
        return sum(1 for move in self.moves if not move.is_removed)

    @property
    def removed(self) -> int:
        """How many moves the user took out."""
        return len(self.moves) - self.kept


@dataclass(frozen=True)
class Snapshot:
    """The domain chapter of one chapter row, with the ids of its faculties and contracts.

    Example:
        >>> snapshot = Chapter.objects.get_snapshot(chapter_id)  # doctest: +SKIP
        >>> snapshot.report().capacity  # doctest: +SKIP
        120
    """

    chapter_id: int
    chapter: Chapter
    faculty_ids: dict[Faculty, int]
    contract_ids: dict[Employee, int]
    employees: dict[int, Employee]  # by employee row id

    def report(self) -> ChapterReport:
        """Evaluate the whole chapter with the domain."""
        return evaluate_chapter(self.chapter)

    def faculty_of(self, faculty_id: int | None) -> Faculty | None:
        """The domain faculty of a faculty row id (None: unsigned, or not in this chapter)."""
        if faculty_id is None:
            return None

        return next((f for f, pk in self.faculty_ids.items() if pk == faculty_id), None)

    def numbers(self, faculty_id: int) -> ChapterFaculty:
        """The faculty with this chapter's numbers."""
        faculty = self.faculty_of(faculty_id)

        assert faculty is not None  # noqa: S101 - faculty ids come from this snapshot

        return self.chapter.faculty(faculty)

    def faculty_id(self, faculty: Faculty | None) -> int | None:
        """The row id of a domain faculty (None: unsigned)."""
        return None if faculty is None else self.faculty_ids[faculty]

    def contract_of(self, employee_id: int) -> Contract | None:
        """The domain contract of an employee row id."""
        return self.chapter.contract_of(self.employees[employee_id])

    def moved(self, employee: Employee, faculty_id: int | None) -> "Snapshot":
        """Preview of a drop: the moved contract goes last, as it would be signed last."""
        contract = self.chapter.contract_of(employee)

        assert contract is not None  # noqa: S101 - only employees with a contract are moved

        others = tuple(c for c in self.chapter.contracts if c.employee != employee)

        moved = contract.signed_to(self.faculty_of(faculty_id))

        return replace(self, chapter=self.chapter.with_contracts((*others, moved)))

    def optimized(self, strategy: Strategy, max_rounds: int = DEFAULT_ROUNDS) -> "Snapshot":
        """The chapter as the optimizer would re-sign it. Nothing is saved."""
        return replace(self, chapter=optimize(self.chapter, strategy, max_rounds))

    def lanes(self, report: ChapterReport | None = None) -> list[Lane]:
        """The unsigned lane, then one lane per faculty; cards in staff order."""
        report = report or self.report()

        unsigned = Lane(
            None,
            None,
            tuple(
                Card(c, None, self.contract_ids[c.employee])
                for c in in_staff_order(self.chapter.unsigned)
            ),
        )

        faculties = [
            Lane(
                self.faculty_ids[item.faculty],
                faculty_report := report.report_of(item.faculty),
                tuple(
                    Card(c, status, self.contract_ids[c.employee])
                    for c, status in faculty_report.in_staff_order
                ),
            )
            for item in self.chapter.faculties
        ]

        return [unsigned, *faculties]

    def status_counts(self, report: ChapterReport | None = None) -> dict[str, int]:
        """How many contracts are counted, not counted, unsigned, or left out."""
        report = report or self.report()

        signed = [s for faculty in report.faculties for s in faculty.statuses.values()]

        unsigned = self.chapter.unsigned

        return {
            "counted": sum(1 for s in signed if s.is_counted),
            "uncounted": sum(1 for s in signed if not s.is_counted and not s.is_excluded),
            "excluded": sum(1 for s in signed if s.is_excluded)
            + sum(1 for c in unsigned if not c.is_included),
            "unsigned": sum(1 for c in unsigned if c.is_included),
        }

    def drop_previews(self, employee_id: int) -> list[DropPreview]:
        """Every drop the employee's card could make: the unsigned lane, then each faculty."""
        employee = self.employees[employee_id]

        previews = []

        for faculty_id in (None, *self.faculty_ids.values()):
            report = self.moved(employee, faculty_id).report()

            previews.append(DropPreview(faculty_id, report.status_of(employee), report.capacity))

        return previews

    def recommendation(
        self,
        strategy: RecommendationStrategy,
        *,
        kinds: frozenset[HireKind],
        optimize_first: bool = False,
        max_rounds: int = DEFAULT_ROUNDS,
    ) -> Recommendation:
        """The contracts to sign to solve the chapter's problems. Nothing is saved.

        `optimize_first`: re-sign the current contracts the default optimizer's way first,
        so new contracts only fill what moving people cannot.
        """
        chapter = self.optimized(Strategy.MAXIMIZE_STUDENTS, max_rounds) if optimize_first else self

        return recommend(chapter.chapter, strategy, kinds=kinds)

    def optimization(self, strategy: Strategy, max_rounds: int = DEFAULT_ROUNDS) -> Optimization:
        """Run the optimizer and compare its placement with the current one."""
        return self.review(strategy, self.optimized(strategy, max_rounds).placements())

    def review(
        self,
        strategy: Strategy,
        placements: Mapping[int, int | None],
        *,
        removed: Collection[int] = (),
        substitutes: Mapping[int, int] | None = None,
    ) -> Optimization:
        """A proposed placement next to the current one, as the user trimmed it.

        Args:
            strategy: the strategy that proposed it.
            placements: contract id -> faculty id (None: unsigned): the whole proposal.
            removed: the ids of the moved contracts left where they are.
            substitutes: a moved contract's id -> the id of the contract moved in its place.

        Raises:
            UserError: a faculty or a substitute the proposal cannot have.
        """
        substitutes = substitutes or {}

        current = self.placements()

        contracts = {self.contract_ids[c.employee]: c for c in self.chapter.contracts}

        proposal = {pk: placements.get(pk, faculty_id) for pk, faculty_id in current.items()}

        moved = [pk for pk, faculty_id in current.items() if proposal[pk] != faculty_id]

        staying = set(current) - set(moved)

        applied = self.placed(self.resolved(proposal, removed=removed, substitutes=substitutes))

        moves = tuple(
            Move(
                contracts[pk].employee,
                applied.sign(contracts[pk], proposal[pk]),
                contracts[pk].faculty,
                applied.faculty_of(proposal[pk]),
                contract_id=pk,
                substitutes=tuple(
                    Substitute(other.employee, self.contract_ids[other.employee])
                    for other in substitutes_for(self.chapter, contracts[pk])
                    if self.contract_ids[other.employee] in staying
                ),
                chosen_id=substitutes.get(pk, pk),
                is_removed=pk in removed,
            )
            for pk in moved
        )

        return Optimization(
            strategy=strategy,
            before=self.report(),
            after=applied.report(),
            before_outcome=outcome_of(self.chapter),
            after_outcome=outcome_of(applied.chapter, self.chapter),
            moves=moves,
            placements=proposal,
        )

    def resolved(
        self,
        placements: Mapping[int, int | None],
        *,
        removed: Collection[int] = (),
        substitutes: Mapping[int, int] | None = None,
    ) -> dict[int, int | None]:
        """The placements to apply: `removed` contracts left out, substitutes moved instead.

        Raises:
            UserError: a substitute that cannot make its move (see `substituted`).
        """
        kept = {pk: faculty_id for pk, faculty_id in placements.items() if pk not in removed}

        chosen = {pk: other for pk, other in (substitutes or {}).items() if pk in kept}

        return self.substituted(kept, chosen)

    def placed(self, placements: Mapping[int, int | None]) -> "Snapshot":
        """The chapter with each contract id signed to its faculty id (None: unsigned).

        Raises:
            UserError: a faculty id is not one of the chapter's.
        """
        by_employee = {
            employee: placements[pk]
            for employee, pk in self.contract_ids.items()
            if pk in placements
        }

        contracts = tuple(
            self.sign(contract, by_employee[contract.employee])
            if contract.employee in by_employee
            else contract
            for contract in self.chapter.contracts
        )

        return replace(self, chapter=self.chapter.with_contracts(contracts))

    def sign(self, contract: Contract, faculty_id: int | None) -> Contract:
        """`contract` signed to a faculty row id (None: unsigned).

        Raises:
            UserError: the faculty id is not one of the chapter's.
        """
        faculty = self.faculty_of(faculty_id)

        if faculty_id is not None and faculty is None:
            raise UserError(_("a faculty of this placement is not in the chapter."))

        return contract.signed_to(faculty)

    def placements(self) -> dict[int, int | None]:
        """Contract id -> faculty id (None: unsigned), to save a placement."""
        return {
            self.contract_ids[c.employee]: self.faculty_id(c.faculty)
            for c in self.chapter.contracts
        }

    def substituted(
        self, placements: Mapping[int, int | None], substitutes: Mapping[int, int]
    ) -> dict[int, int | None]:
        """`placements`, each substitute making its contract's move in its place.

        Args:
            placements: contract id -> faculty id (None: unsigned), as `placements()` gives.
            substitutes: a moved contract's id -> the id of the contract moved instead
                (itself: no substitute).

        Raises:
            UserError: a substitute is not one of its contract's (`substitutes_for`), moves
                already, or is chosen for two moves.
        """
        current = self.placements()

        by_id = {
            pk: self.chapter.contract_of(employee) for employee, pk in self.contract_ids.items()
        }

        result = dict(placements)

        chosen: set[int] = set()

        for contract_id, substitute_id in substitutes.items():
            if substitute_id == contract_id:
                continue

            contract = by_id.get(contract_id)

            allowed = {
                self.contract_ids[other.employee]
                for other in (substitutes_for(self.chapter, contract) if contract else ())
            }

            stays = placements.get(substitute_id, current.get(substitute_id)) == current.get(
                substitute_id
            )

            if substitute_id not in allowed or not stays or substitute_id in chosen:
                raise UserError(_("choose another employee: this one cannot make that move."))

            chosen.add(substitute_id)

            result[substitute_id] = placements.get(contract_id, current[contract_id])
            result[contract_id] = current[contract_id]

        return result


def _other(value: Enum) -> Enum:
    """The other value of a two-valued domain enum (fulltime: parttime)."""
    return next(member for member in type(value) if member is not value)
