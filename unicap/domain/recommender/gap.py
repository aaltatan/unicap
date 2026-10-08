"""How far a faculty is from having no problem, in teachers.

Every problem is a number of people or of students:
  people  teachers missing to every minimum: min_teachers, min specialized / supported,
          min shares, min staff percentage
  seats   current students without a seat, and students missing to target_students
          (a faculty with a target must reach it, not only seat its current students)

`distance` puts them on one scale, whole teachers: the seats need one PhD per
`students_per_phd` students. A minimum rounded to whole people can stay missed after a
hire that still helps (a 50% staff minimum of 3 PhDs needs 2 staff, of 4 PhDs still 2,
of 5 PhDs 3), so `exact` measures the same problems before rounding: a hire helps when it
shortens the distance, or keeps it and shortens the exact one.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import ceil

from unicap.domain.capacity import FacultyReport
from unicap.domain.utils import as_fraction


@dataclass(frozen=True, slots=True)
class Gap:
    people: int = 0
    seats: int = 0
    students_per_phd: int = 1
    exact: Fraction = Fraction(0)  # the same problems, in teachers, before any rounding

    @property
    def distance(self) -> int:
        """Teachers missing: the people, and one PhD per `students_per_phd` seats."""
        return self.people + ceil(self.seats / self.students_per_phd)

    @property
    def key(self) -> tuple[int, Fraction]:
        """Lower is closer: whole teachers missing first, then the exact measure."""
        return self.distance, self.exact

    @property
    def is_closed(self) -> bool:
        return self.distance == 0


def gap_of(report: FacultyReport) -> Gap:
    calculation = report.calculation

    people = calculation.teacher_shortage + calculation.share_shortage
    people += calculation.staff_shortage

    seats = calculation.seat_shortage + calculation.target_shortfall

    spp = report.faculty.students_per_phd

    exact = calculation.teacher_shortage + Fraction(seats, spp)
    exact += _staff_exact(report) + _shares_exact(report)

    return Gap(people, seats, spp, exact)


def _staff_exact(report: FacultyReport) -> Fraction:
    """Fulltime staff missing to min_staff_percentage, before rounding (0 when met)."""
    if not report.calculation.staff_shortage:
        return Fraction(0)

    signed = report.calculation.signed_roster

    phds = signed.phds + signed.unaccepted_phds

    needed = phds * as_fraction(report.faculty.min_staff_percentage) / 100

    return max(Fraction(0), needed - signed.fulltime_staff)


def _shares_exact(report: FacultyReport) -> Fraction:
    """Teachers missing to every min share, before rounding (only the shares missed)."""
    if not report.calculation.share_shortage:
        return Fraction(0)

    counted = report.calculation.counted_roster

    total = Fraction(0)

    for share in report.faculty.shares:
        needed = counted.heads * as_fraction(share.lower_bound) / 100

        total += max(Fraction(0), needed - counted.of(share.specialization).heads)

    return total
