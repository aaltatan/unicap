"""`recommend`: the contracts to sign so that every faculty has no problem left.

Faculties are independent (a contract counts in the faculty it is signed to), so each is
solved on its own, greedily: sign the strategy's best contract among those that bring the
faculty closer (gap.py), until nothing is missing, nothing helps any more, or `max_hires`.
Masters are signed by the PhD (their row's `masters_per_phd` at a time): one master alone
may round to no PhD at all. A kind the row does not count (its `contract_type`, masters
left out) is never suggested.
"""

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import count

from unicap.domain.capacity import ChapterReport, evaluate_chapter, evaluate_faculty
from unicap.domain.enums import SpecializationType
from unicap.domain.models import (
    Chapter,
    ChapterFaculty,
    Contract,
    Employee,
    Faculty,
    Share,
    Specialization,
)
from unicap.domain.recommender.gap import Gap, gap_of
from unicap.domain.recommender.hires import ALL_KINDS, Hire, HireKind
from unicap.domain.recommender.strategies import Candidate, RecommendationStrategy
from unicap.domain.salaries import salary_class

DEFAULT = RecommendationStrategy.FEWEST_CONTRACTS

TRIAL_IDS = -1_000_000_000  # employees of a contract only tried, never signed


@dataclass(frozen=True, slots=True)
class Recommendation:
    """The contracts to sign, and the chapter before and after signing them."""

    strategy: RecommendationStrategy
    hires: tuple[Hire, ...]
    before: ChapterReport
    after: ChapterReport
    meet_targets: bool = False

    @property
    def contracts(self) -> int:
        """How many contracts to sign in all."""
        return sum(hire.count for hire in self.hires)

    @property
    def is_solved(self) -> bool:
        """No problem is left once the hires are signed."""
        if not self.after.is_compliant:
            return False

        return not self.meet_targets or self.after.target_shortfall == 0

    def hires_of(self, faculty: Faculty) -> tuple[Hire, ...]:
        return tuple(hire for hire in self.hires if hire.faculty == faculty)


def recommend(
    chapter: Chapter,
    strategy: RecommendationStrategy = DEFAULT,
    *,
    kinds: frozenset[HireKind] = ALL_KINDS,
    meet_targets: bool = False,
    max_hires: int = 200,
) -> Recommendation:
    """Recommend the contracts to sign so that the chapter's problems are solved.

    Args:
        chapter: the chapter as it is (its current placement is kept).
        strategy: which helping contract comes first.
        kinds: the kinds of contract the university is willing to sign.
        meet_targets: also reach every faculty's target_students.
        max_hires: the most contracts tried per faculty.

    Example:
        ```python
        recommendation = recommend(chapter, RecommendationStrategy.LOW_SALARIES)
        recommendation.contracts, recommendation.is_solved
        ```
    """
    ids = count(-1, -1)  # new employees get ids no row has

    search = _Search(chapter, strategy, kinds, meet_targets=meet_targets)

    signed = [
        pair
        for item in chapter.faculties
        for pair in search.hires_for(item, max_hires=max_hires, ids=ids)
    ]

    contracts = [contract for _, contract in signed]

    after = replace(
        chapter,
        contracts=(*chapter.contracts, *contracts),
        employees=(*chapter.employees, *(c.employee for c in contracts)),
    )

    return Recommendation(
        strategy=strategy,
        hires=_grouped(signed),
        before=evaluate_chapter(chapter),
        after=evaluate_chapter(after),
        meet_targets=meet_targets,
    )


class _Search:
    """The greedy search of one chapter's hires, faculty by faculty."""

    def __init__(
        self,
        chapter: Chapter,
        strategy: RecommendationStrategy,
        kinds: frozenset[HireKind],
        *,
        meet_targets: bool,
    ) -> None:
        self.chapter = chapter
        self.strategy = strategy
        self.kinds = sorted(kinds)
        self.meet_targets = meet_targets

    def hires_for(
        self, faculty: ChapterFaculty, *, max_hires: int, ids: Iterator[int]
    ) -> list[tuple[HireKind, Contract]]:
        """Sign the best helping contract until no problem is left or none helps."""
        contracts = list(self.chapter.contracts_of(faculty.faculty))

        hired: list[tuple[HireKind, Contract]] = []

        gap = self.gap(faculty, contracts)

        while not gap.is_closed and len(hired) < max_hires:
            best = self.best(faculty, contracts, gap)

            if best is None:  # nothing helps any more: what is left needs more than hires
                break

            new = _contracts(best.kind, best.specialization, faculty.faculty, best.size, ids)

            hired += [(best.kind, contract) for contract in new]

            contracts += new

            gap = self.gap(faculty, contracts)

        return hired

    def best(
        self, faculty: ChapterFaculty, contracts: list[Contract], gap: Gap
    ) -> Candidate | None:
        """The strategy's best candidate among those that shorten the gap (None: none does)."""
        candidates = [
            candidate
            for order, specialization in enumerate(faculty.faculty.specializations)
            if specialization.is_active
            for kind in self.kinds
            if (candidate := self.candidate(faculty, contracts, gap, kind, specialization, order))
        ]

        return min(candidates, key=self.strategy.key, default=None)

    def candidate(  # noqa: PLR0913 - the faculty as it is, and the contract tried
        self,
        faculty: ChapterFaculty,
        contracts: list[Contract],
        gap: Gap,
        kind: HireKind,
        specialization: Specialization,
        order: int,
    ) -> Candidate | None:
        """Try signing `kind` of `specialization`: a candidate if it shortens the gap."""
        size = self.size(kind, faculty.share_of(specialization))

        if size == 0:
            return None

        trial = _contracts(kind, specialization, faculty.faculty, size, count(TRIAL_IDS, -1))

        after = self.gap(faculty, [*contracts, *trial])

        if after.key >= gap.key:
            return None

        return Candidate(
            specialization=specialization,
            kind=kind,
            size=size,
            progress=Fraction(gap.distance - after.distance, size),
            exact_progress=(gap.exact - after.exact) / size,
            salary=salary_class(faculty.faculty, trial[0]),
            is_specialized=faculty.type_of(specialization) is SpecializationType.SPECIALIZED,
            order=order,
        )

    def size(self, kind: HireKind, share: Share) -> int:
        """How many contracts a candidate signs at once (0: the row never counts this kind)."""
        contract_type, _, _ = kind.terms

        if not share.allows(contract_type):
            return 0

        if kind is not HireKind.MASTER:
            return 1

        return share.masters_per_phd if share.calculate_masters else 0

    def gap(self, faculty: ChapterFaculty, contracts: list[Contract]) -> Gap:
        report = evaluate_faculty(faculty, contracts)

        return gap_of(report, meet_targets=self.meet_targets)


def _contracts(
    kind: HireKind,
    specialization: Specialization,
    faculty: Faculty,
    size: int,
    ids: Iterator[int],
) -> list[Contract]:
    """`size` new contracts, each of a new employee (`ids` gives their ids)."""
    return [
        kind.contract(Employee(next(ids), f"{specialization.name} (new)", specialization), faculty)
        for _ in range(size)
    ]


def _grouped(signed: list[tuple[HireKind, Contract]]) -> tuple[Hire, ...]:
    """The signed contracts as hires: one per faculty, specialization and kind, in order."""
    counts: Counter[tuple[Faculty, Specialization, HireKind]] = Counter()

    for kind, contract in signed:
        assert contract.faculty is not None  # noqa: S101 - every hire is signed

        counts[contract.faculty, contract.employee.specialization, kind] += 1

    return tuple(
        Hire(faculty, specialization, kind, how_many)
        for (faculty, specialization, kind), how_many in counts.items()
    )
