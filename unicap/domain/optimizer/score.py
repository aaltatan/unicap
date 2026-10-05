"""What one faculty contributes to a placement. Scores add up across faculties."""

from dataclasses import dataclass, fields
from typing import Any

from unicap.domain.capacity import FacultyReport
from unicap.domain.enums import ContractStatus
from unicap.domain.salaries import MOST_EXPENSIVE_FIRST, salary_counts

NO_SALARIES = (0,) * len(MOST_EXPENSIVE_FIRST)

# signed, but no number of any specialization: only in the staff ratio's bottom
_NEVER_COUNTED = (ContractStatus.SPECIALIZATION_NOT_ALLOWED, ContractStatus.FACULTY_NOT_ALLOWED)


@dataclass(frozen=True, slots=True)
class Score:
    violations: int = 0
    students: int = 0  # the faculty's capacity, capped by its max_students
    teachers: int = 0  # counted contracts
    signed: int = 0  # included contracts signed to the faculty
    uncounted: int = 0
    target_shortfall: int = 0
    seat_shortage: int = 0  # current students without a seat
    teacher_shortage: int = 0  # PhDs missing to reach min_teachers
    staff: int = 0  # fulltime staff PhDs (the staff ratio's top)
    phds: int = 0  # every signed PhD (the staff ratio's bottom)
    salaries: tuple[int, ...] = NO_SALARIES  # contracts per salary class, most expensive first

    @classmethod
    def of(cls, report: FacultyReport) -> "Score":
        included = report.included

        uncounted = len(report.uncounted)

        phds = [c for c in included if c.is_phd]

        accepted = [c for c in phds if report.statuses[c] not in _NEVER_COUNTED]

        return cls(
            violations=len(report.violations),
            students=report.capacity,
            teachers=len(included) - uncounted,
            signed=len(included),
            uncounted=uncounted,
            target_shortfall=report.target_shortfall,
            seat_shortage=report.seat_shortage,
            teacher_shortage=report.teacher_shortage,
            staff=sum(1 for c in accepted if c.is_fulltime and c.is_staff),
            phds=len(phds),
            salaries=salary_counts(report.faculty.faculty, included),
        )

    def __add__(self, other: "Score") -> "Score":
        return self._combine(other, 1)

    def __sub__(self, other: "Score") -> "Score":
        return self._combine(other, -1)

    def _combine(self, other: "Score", sign: int) -> "Score":
        values: dict[str, Any] = {}

        for field in fields(self):
            mine, theirs = getattr(self, field.name), getattr(other, field.name)

            if isinstance(mine, tuple):
                values[field.name] = tuple(a + sign * b for a, b in zip(mine, theirs, strict=True))

            else:
                values[field.name] = mine + sign * theirs

        return Score(**values)
