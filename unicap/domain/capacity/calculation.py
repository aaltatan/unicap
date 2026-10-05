"""Calculation: what counted numbers allow. No contract here, only `Roster`s.

Counting (`counting.py`) decides who is counted; this turns the numbers it leaves into
capacity, staff percentage and violations. Being numbers only, it also runs on numbers
typed in by hand (`unicap.domain.capacity.numbers`).

Example:
    >>> from unicap.domain.models import Faculty, Specialization
    >>> biology = Specialization("Biology")
    >>> faculty = ChapterFaculty(Faculty("Science", specialized=(biology,)), students_per_phd=10)
    >>> counted = Roster((SpecializationCount(biology, fulltime_staff=3, masters=3),))
    >>> calculate(faculty, counted).capacity  # 3 PhDs + 3 masters (one PhD, rounded down)
    40
"""

from dataclasses import dataclass
from fractions import Fraction

from unicap.domain.capacity import students
from unicap.domain.capacity.head_count import HeadCount, head_count_of
from unicap.domain.capacity.mix import Mix, mix_of
from unicap.domain.capacity.roster import Roster, SpecializationCount
from unicap.domain.capacity.violations import (
    Violation,
    current_students_violations,
    share_shortages,
    share_violations,
    staff_percentage,
    staff_shortage,
    staff_violations,
    teacher_shortages,
    teacher_violations,
    type_shortages,
    type_violations,
)
from unicap.domain.models import ChapterFaculty

__all__ = ["Calculation", "Roster", "SpecializationCount", "calculate"]


@dataclass(frozen=True, slots=True)
class Calculation:
    """A faculty's numbers, from its signed and counted teachers (build it with `calculate`).

    `teaching_capacity`: students the counted teachers allow, before the faculty's
    max_students; `capacity`: what it may take, capped by max_students.
    """

    faculty: ChapterFaculty
    signed_roster: Roster
    counted_roster: Roster
    signed: HeadCount
    counted: HeadCount
    staff_percentage: Fraction
    teaching_capacity: int
    capacity: int
    violations: tuple[Violation, ...]

    @property
    def mix(self) -> Mix:
        """The signed teachers as percentages: specialized, fulltime, PhDs and their opposites."""
        return mix_of(self.signed)

    @property
    def unused_teaching_capacity(self) -> int:
        """Teaching capacity lost above max_students: teachers who could serve elsewhere."""
        return self.teaching_capacity - self.capacity

    @property
    def is_compliant(self) -> bool:
        return not self.violations

    @property
    def target_shortfall(self) -> int:
        """Students missing to reach target_students (0 when reached or no target)."""
        if self.faculty.target_students is None:
            return 0

        return max(0, self.faculty.target_students - self.capacity)

    @property
    def seat_shortage(self) -> int:
        """Current students without a seat."""
        if self.faculty.current_students is None:
            return 0

        return max(0, self.faculty.current_students - self.capacity)

    @property
    def free_seats(self) -> int | None:
        """Capacity left for new students, or None when current_students is unknown."""
        if self.faculty.current_students is None:
            return None

        return self.capacity - self.faculty.current_students

    @property
    def teacher_shortage(self) -> int:
        """Teachers missing to reach every min_teachers, and the min specialized / supported."""
        shortages = [
            *teacher_shortages(self.faculty, self.counted_roster).values(),
            *type_shortages(self.faculty, self.counted_roster).values(),
        ]

        return sum(minimum - count for count, minimum in shortages)

    @property
    def share_shortage(self) -> int:
        """Teachers missing to reach every min share."""
        shortages = share_shortages(self.faculty, self.signed_roster, self.counted_roster)

        return sum(required - count for count, required in shortages.values())

    @property
    def staff_shortage(self) -> int:
        """Fulltime staff missing to reach min_staff_percentage."""
        staff, required = staff_shortage(self.faculty, self.signed_roster)

        return max(0, required - staff)


def calculate(
    faculty: ChapterFaculty,
    counted: Roster,
    signed: Roster | None = None,
) -> Calculation:
    """Calculate a faculty from numbers that are counted already.

    `signed` (default: the counted ones) are every teacher signed to the faculty,
    uncounted included: only the staff percentage reads them.
    """
    signed = counted if signed is None else signed

    counted_heads = head_count_of(faculty, counted)

    capacity = students.capacity(faculty, counted_heads)

    violations = (
        *staff_violations(faculty, signed),
        *share_violations(faculty, signed, counted),
        *current_students_violations(faculty, capacity),
        *teacher_violations(faculty, counted),
        *type_violations(faculty, counted),
    )

    return Calculation(
        faculty=faculty,
        signed_roster=signed,
        counted_roster=counted,
        signed=head_count_of(faculty, signed),
        counted=counted_heads,
        staff_percentage=staff_percentage(signed),
        teaching_capacity=students.teaching_capacity(faculty, counted_heads),
        capacity=capacity,
        violations=violations,
    )
