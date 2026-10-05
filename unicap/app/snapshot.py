"""A chapter as the board sees it: the domain aggregate plus the row ids to write back."""

from dataclasses import dataclass, replace

from unicap.domain import (
    Chapter,
    ChapterFaculty,
    ChapterReport,
    Contract,
    ContractStatus,
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
)

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
class Move:
    """One contract the optimizer re-signs."""

    employee: Employee
    contract: Contract
    before: Faculty | None
    after: Faculty | None


@dataclass(frozen=True)
class Optimization:
    """A strategy's placement next to the current one. Nothing is saved."""

    strategy: Strategy
    before: ChapterReport
    after: ChapterReport
    before_outcome: Outcome
    after_outcome: Outcome
    moves: tuple[Move, ...]
    placements: dict[int, int | None]  # contract id -> faculty id, to apply it


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
        meet_targets: bool = False,
        optimize_first: bool = False,
        max_rounds: int = DEFAULT_ROUNDS,
    ) -> Recommendation:
        """The contracts to sign to solve the chapter's problems. Nothing is saved.

        `optimize_first`: re-sign the current contracts the default optimizer's way first,
        so new contracts only fill what moving people cannot.
        """
        chapter = self.optimized(Strategy.MAXIMIZE_STUDENTS, max_rounds) if optimize_first else self

        return recommend(chapter.chapter, strategy, kinds=kinds, meet_targets=meet_targets)

    def optimization(self, strategy: Strategy, max_rounds: int = DEFAULT_ROUNDS) -> Optimization:
        """Run the optimizer and compare its placement with the current one."""
        optimized = self.optimized(strategy, max_rounds)

        before = {c.employee: c for c in self.chapter.contracts}

        moves = tuple(
            Move(c.employee, c, before[c.employee].faculty, c.faculty)
            for c in optimized.chapter.contracts
            if before[c.employee].faculty != c.faculty
        )

        return Optimization(
            strategy=strategy,
            before=self.report(),
            after=optimized.report(),
            before_outcome=outcome_of(self.chapter),
            after_outcome=outcome_of(optimized.chapter, self.chapter),
            moves=moves,
            placements=optimized.placements(),
        )

    def placements(self) -> dict[int, int | None]:
        """Contract id -> faculty id (None: unsigned), to save a placement."""
        return {
            self.contract_ids[c.employee]: self.faculty_id(c.faculty)
            for c in self.chapter.contracts
        }
