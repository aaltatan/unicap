"""What "the best next contract" means: one key per strategy, lower is better.

Every strategy only picks among contracts that bring the faculty closer to having no
problem (see gap.py); it decides which of those comes first:

  FEWEST_CONTRACTS       the most progress per contract, then the cheapest
  LOW_SALARIES           the cheapest salary class that helps, then the most progress
                         (see unicap.domain.salaries)
  FULLTIME_STAFF_FIRST   fulltime staff PhDs when they help, then the most progress
  BORROWED_FIRST         fulltime borrowed PhDs when they help, then the most progress
  SPECIALIZED_FIRST      specializations the faculty specializes in, then the most progress
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import auto
from fractions import Fraction
from typing import TypeAlias

from unicap.domain.enums import StrEnum
from unicap.domain.models import Specialization
from unicap.domain.recommender.hires import HireKind
from unicap.domain.salaries import SalaryClass

Key: TypeAlias = tuple[int | Fraction, ...]


@dataclass(frozen=True, slots=True)
class Candidate:
    """A possible next signing: `size` contracts of `kind` (masters come by the PhD)."""

    specialization: Specialization
    kind: HireKind
    size: int
    progress: Fraction  # whole teachers missing, fewer per contract signed
    exact_progress: Fraction  # the same before rounding (see gap.py)
    salary: SalaryClass
    is_specialized: bool
    order: int  # the specialization's place in the faculty: the tie-breaker


class RecommendationStrategy(StrEnum):
    FEWEST_CONTRACTS = auto()
    LOW_SALARIES = auto()
    FULLTIME_STAFF_FIRST = auto()
    BORROWED_FIRST = auto()
    SPECIALIZED_FIRST = auto()

    def key(self, candidate: Candidate) -> Key:
        """Lower is better."""
        return (*_KEYS[self](candidate), candidate.order)


def _most_progress(c: Candidate) -> Key:
    return -c.progress, -c.exact_progress, c.salary


_KEYS: dict[RecommendationStrategy, Callable[[Candidate], Key]] = {
    RecommendationStrategy.FEWEST_CONTRACTS: _most_progress,
    RecommendationStrategy.LOW_SALARIES: lambda c: (c.salary, -c.progress, -c.exact_progress),
    RecommendationStrategy.FULLTIME_STAFF_FIRST: lambda c: (
        c.kind is not HireKind.FULLTIME_STAFF,
        *_most_progress(c),
    ),
    RecommendationStrategy.BORROWED_FIRST: lambda c: (
        c.kind is not HireKind.FULLTIME_BORROWED,
        *_most_progress(c),
    ),
    RecommendationStrategy.SPECIALIZED_FIRST: lambda c: (
        not c.is_specialized,
        *_most_progress(c),
    ),
}
