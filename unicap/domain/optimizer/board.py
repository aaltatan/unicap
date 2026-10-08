"""The optimizer's working state: where every contract is and what each faculty scores."""

from collections.abc import Sequence

from unicap.domain.capacity import evaluate_faculty
from unicap.domain.models import Chapter, ChapterFaculty, Contract, Employee, Faculty
from unicap.domain.optimizer.outcome import Outcome
from unicap.domain.optimizer.placement import Target, accepting
from unicap.domain.optimizer.score import Score
from unicap.domain.optimizer.strategies import Key, Strategy


class Board:
    """Mutable on purpose: it is rescored thousands of times and never leaves the optimizer.

    Only the faculties a move touches are re-evaluated; the totals are kept up to date.
    """

    def __init__(self, chapter: Chapter, strategy: Strategy) -> None:
        # contracts move between faculties; each one is scored with the chapter's numbers
        self.numbers: dict[Faculty, ChapterFaculty] = {f.faculty: f for f in chapter.faculties}

        self.faculties = tuple(self.numbers)

        faculties = self.faculties

        self.strategy = strategy

        self.chapter_max = chapter.max_students

        self.origin: dict[Employee, Target] = {c.employee: c.faculty for c in chapter.contracts}

        self.contracts: dict[Faculty, list[Contract]] = {faculty: [] for faculty in faculties}

        # empty faculties count too: a missing target or unseated students show from the start
        self.scores: dict[Faculty, Score] = {
            faculty: self._score(faculty, []) for faculty in faculties
        }

        self.total = sum(self.scores.values(), Score())

        self.moves = 0

        self.faculty_of: dict[Employee, Target] = {}

        self.contract_of: dict[Employee, Contract] = {}

    # --- reading --------------------------------------------------------------------

    def outcome(self) -> Outcome:
        return Outcome.of(self.total, self.chapter_max, self.moves, self.scores.values())

    def is_movable(self, contract: Contract) -> bool:
        """Tell whether the search may place a contract: it takes part and is not locked in.

        (Where a contract counts is each faculty's say.)
        """
        return contract.is_included and not contract.is_pinned

    def key(self) -> Key:
        return self.strategy.key(self.outcome())

    def key_if(self, contract: Contract, target: Target) -> Key:
        """Return the strategy's key if `contract` moved to `target` (nothing changes)."""
        employee = contract.employee

        source = self.faculty_of.get(employee)

        scores = dict(self.scores)

        if source is not None:
            scores[source] = self._score(source, self._without(source, employee))

        if target is not None:
            scores[target] = self._score(target, [*self.contracts[target], contract])

        total = self.total

        for faculty in {source, target} - {None}:
            total += scores[faculty] - self.scores[faculty]  # type: ignore[index]

        moves = self.moves - self._is_moved(employee) + (target != self.origin.get(employee))

        outcome = Outcome.of(total, self.chapter_max, moves, scores.values())

        return self.strategy.key(outcome)

    def best_faculty(self, contract: Contract, faculties: Sequence[Faculty]) -> Target:
        """Best of `faculties`, never unsigned while one exists.

        A faculty whose shares are still incomplete scores worse than an empty one,
        so choosing "unsigned" here would starve it before it is built.
        """
        if not faculties:
            return None

        def preference(faculty: Faculty) -> tuple[Key, bool, int]:
            # on equal keys: where it is counted (a master alone may round to no PhD yet,
            # but the next one makes one), then spread contracts across faculties
            return (
                self.key_if(contract, faculty),
                self.counts_in(contract, faculty),
                -len(self.contracts[faculty]),
            )

        return max(faculties, key=preference)

    def counts_in(self, contract: Contract, faculty: Faculty) -> bool:
        """Whether `contract` would be counted signed to `faculty` (nothing changes)."""
        contracts = [*self._without(faculty, contract.employee), contract]

        report = evaluate_faculty(self.numbers[faculty], contracts)

        return report.statuses[contract].is_counted

    # --- changing -------------------------------------------------------------------

    def move(self, contract: Contract, target: Target) -> None:
        employee = contract.employee

        source = self.faculty_of.get(employee)

        self.moves -= self._is_moved(employee)

        if source is not None:
            self._set_contracts(source, self._without(source, employee))

        if target is not None:
            self._set_contracts(target, [*self.contracts[target], contract])

        self.faculty_of[employee] = target

        self.contract_of[employee] = contract

        self.moves += self._is_moved(employee)

    def improve(self, max_rounds: int) -> None:
        for _ in range(max_rounds):
            if not self._improve_once():
                return

    def _improve_once(self) -> bool:
        """Move every contract that has a strictly better place. True if anything moved."""
        moved = False

        for contract in list(self.contract_of.values()):
            if not self.is_movable(contract):
                continue

            current = self.faculty_of[contract.employee]

            targets = [t for t in [*accepting(self.faculties, contract), None] if t != current]

            keys = {target: self.key_if(contract, target) for target in targets}

            best = max(keys, key=lambda target: keys[target], default=current)

            if best != current and keys[best] > self.key():
                self.move(contract, best)

                moved = True

        return moved

    def _set_contracts(self, faculty: Faculty, contracts: list[Contract]) -> None:
        score = self._score(faculty, contracts)

        self.total += score - self.scores[faculty]

        self.contracts[faculty] = contracts

        self.scores[faculty] = score

    def _without(self, faculty: Faculty, employee: Employee) -> list[Contract]:
        return [c for c in self.contracts[faculty] if c.employee != employee]

    def _is_moved(self, employee: Employee) -> bool:
        placed = employee in self.faculty_of

        return placed and self.faculty_of[employee] != self.origin.get(employee)

    def _score(self, faculty: Faculty, contracts: Sequence[Contract]) -> Score:
        report = evaluate_faculty(self.numbers[faculty], contracts)

        return Score.of(report)
