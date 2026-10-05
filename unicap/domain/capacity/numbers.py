"""Capacity from numbers alone: no people, no contracts, no chapter rows.

For a calculator (an API, a what-if form): give each faculty its numbers and how many
teachers of each kind each accepted specialization has.

  count_roster     apply the counting rules to typed-in numbers: who would be counted
  evaluate_numbers a whole chapter of numbers: each faculty's calculation, the capacity

With `count=False` the numbers are taken as counted already and only calculated.

Example:
    >>> from unicap.domain.models import Faculty, Specialization
    >>> biology = Specialization("Biology")
    >>> science = ChapterFaculty(Faculty("Science", specialized=(biology,)), students_per_phd=10)
    >>> signed = Roster((SpecializationCount(biology, fulltime_staff=2, parttime=5),))
    >>> evaluate_numbers((FacultyNumbers(science, signed),)).capacity  # 2 parttime counted
    40
"""

from dataclasses import dataclass

from unicap.domain.capacity import students
from unicap.domain.capacity.calculation import Calculation, calculate
from unicap.domain.capacity.counting import count_contracts
from unicap.domain.capacity.roster import Roster, SpecializationCount, contracts_of, roster_of
from unicap.domain.models import ChapterFaculty

__all__ = [
    "FacultyNumbers",
    "NumbersReport",
    "Roster",
    "SpecializationCount",
    "count_roster",
    "evaluate_numbers",
]


@dataclass(frozen=True, slots=True)
class FacultyNumbers:
    """A faculty (with its numbers) and its teachers, as numbers."""

    faculty: ChapterFaculty
    teachers: Roster


@dataclass(frozen=True, slots=True)
class NumbersReport:
    faculties: tuple[Calculation, ...]
    max_students: int | None = None

    @property
    def faculties_capacity(self) -> int:
        return sum(item.capacity for item in self.faculties)

    @property
    def teaching_capacity(self) -> int:
        return sum(item.teaching_capacity for item in self.faculties)

    @property
    def capacity(self) -> int:
        return students.capped(self.faculties_capacity, self.max_students)

    @property
    def is_compliant(self) -> bool:
        return all(item.is_compliant for item in self.faculties)


def count_roster(
    faculty: ChapterFaculty,
    signed: Roster,
) -> Roster:
    """The counted part of `signed`: the counting rules, applied to numbers.

    The numbers are signed in the faculty's specialization order, each one's fulltime
    staff first (see `roster.contracts_of`): when a rule cannot count everyone, it
    leaves out the cheapest, then the last.
    """
    contracts = contracts_of(faculty, signed)

    statuses = count_contracts(faculty, contracts)

    return roster_of(faculty, [c for c, status in statuses.items() if status.is_counted])


def evaluate_numbers(
    faculties: tuple[FacultyNumbers, ...],
    *,
    max_students: int | None = None,
    count: bool = True,
) -> NumbersReport:
    """Calculate every faculty from its numbers; `count=False`: they are counted already."""

    def counted(item: FacultyNumbers) -> Roster:
        if count:
            return count_roster(item.faculty, item.teachers)

        return _without_excluded(item.faculty, item.teachers)

    calculations = tuple(
        calculate(
            item.faculty,
            counted=counted(item),
            signed=_without_excluded(item.faculty, item.teachers),
        )
        for item in faculties
    )

    return NumbersReport(calculations, max_students)


def _without_excluded(faculty: ChapterFaculty, roster: Roster) -> Roster:
    """Masters a faculty row does not calculate are not signed teachers either."""
    return Roster(
        tuple(
            item
            if faculty.share_of(item.specialization).calculate_masters
            else SpecializationCount(
                item.specialization, item.fulltime_staff, item.fulltime_borrowed, item.parttime
            )
            for item in roster.counts
        ),
        roster.unaccepted_phds,
    )
