"""Optimizer strategies: what "a better placement" means.

Every strategy puts compliance first (fewer violations, then fewer PhDs missing to
min_teachers, then fewer current students without a seat), then its own goal, then
tie-breakers. A strategy is a key: the
placement with the highest key wins.

  MAXIMIZE_STUDENTS        the most students the ministry allows
  MAXIMIZE_TEACHER_USAGE   the most counted teachers: as few people wasted as possible
  MINIMIZE_OVERFLOW        the lowest share of signed contracts that are not counted
  MEET_TARGETS             reach every faculty's target_students first
  MINIMIZE_CHANGES         become compliant with the fewest re-signed contracts
  MINIMIZE_TEACHERS        the most students with the fewest signed teachers:
                           frees everyone who adds no student
  LESS_SALARIES            the most students with the cheapest team: fewer of the most
                           expensive salary class first (see unicap.domain.salaries)
  BEST_STAFF_PERCENTAGE    the highest staff percentage in the weakest faculty, then
                           overall, then students (trades students for staff share)
"""

from collections.abc import Callable
from enum import auto
from fractions import Fraction
from typing import TypeAlias

from unicap.domain.enums import StrEnum
from unicap.domain.optimizer.outcome import Outcome

Key: TypeAlias = tuple[int | Fraction, ...]


class Strategy(StrEnum):
    MAXIMIZE_STUDENTS = auto()
    MAXIMIZE_TEACHER_USAGE = auto()
    MINIMIZE_OVERFLOW = auto()
    MEET_TARGETS = auto()
    MINIMIZE_CHANGES = auto()
    MINIMIZE_TEACHERS = auto()
    LESS_SALARIES = auto()
    BEST_STAFF_PERCENTAGE = auto()

    def key(self, outcome: Outcome) -> Key:
        """Higher is better."""
        return _KEYS[self](outcome)


def _compliance(o: Outcome) -> Key:
    """Fewer violations first; the shortages show progress before a violation clears."""
    return -o.violations, -o.teacher_shortage, -o.seat_shortage


_KEYS: dict[Strategy, Callable[[Outcome], Key]] = {
    Strategy.MAXIMIZE_STUDENTS: lambda o: (*_compliance(o), o.students, -o.uncounted, -o.moves),
    Strategy.MAXIMIZE_TEACHER_USAGE: lambda o: (*_compliance(o), o.teachers, o.students, -o.moves),
    Strategy.MINIMIZE_OVERFLOW: lambda o: (
        *_compliance(o),
        -o.overflow_percentage,
        o.students,
        -o.moves,
    ),
    Strategy.MEET_TARGETS: lambda o: (
        *_compliance(o),
        -o.target_shortfall,
        o.students,
        -o.uncounted,
        -o.moves,
    ),
    Strategy.MINIMIZE_CHANGES: lambda o: (*_compliance(o), -o.moves, o.students, -o.uncounted),
    Strategy.MINIMIZE_TEACHERS: lambda o: (*_compliance(o), o.students, -o.signed, -o.moves),
    Strategy.LESS_SALARIES: lambda o: (
        *_compliance(o),
        o.students,
        *(-count for count in o.salaries),
        -o.moves,
    ),
    Strategy.BEST_STAFF_PERCENTAGE: lambda o: (
        *_compliance(o),
        o.lowest_staff_percentage,
        o.staff_percentage,
        o.students,
        -o.moves,
    ),
}
