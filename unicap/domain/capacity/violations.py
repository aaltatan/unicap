"""Rules 5-7: what makes a faculty non-compliant. Every minimum is a violation, never a drop.

All of them read numbers only (`Roster`s), so they hold for typed-in numbers too:
  - fulltime staff below `min_staff_percentage` of every signed PhD (uncounted included),
    rounded up to whole staff by default (`staff_rounding`)
  - a specialization below its min share of the counted teachers (PhDs and masters),
    rounded up to whole teachers by default (`min_share_rounding`)
  - a specialization with fewer counted teachers (PhDs and masters) than min_teachers
  - fewer counted specialized / supported PhDs than the faculty's minimum of that type
  - more current students than the capacity
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from fractions import Fraction

from unicap.domain.capacity.roster import Roster
from unicap.domain.enums import SpecializationType, ViolationKind
from unicap.domain.models import ChapterFaculty
from unicap.domain.rounding import round_count
from unicap.domain.utils import as_fraction, percent_of


@dataclass(frozen=True, slots=True)
class Violation:
    """A broken rule: `message` in English, `params` its values (for a translated sentence).

    `params` always holds `faculty` (its name), and by kind:

    - STAFF_RATIO_TOO_LOW: `percentage`, `minimum`, `staff`, `required`
    - CURRENT_STUDENTS_OVER_CAPACITY: `current_students`, `capacity`
    - TOO_FEW_TEACHERS: `specialization`, `counted`, `minimum`
    - TOO_FEW_OF_TYPE: `type` (a `SpecializationType`), `counted`, `minimum`
    - SPECIALIZATION_SHARE_TOO_LOW: `specialization`, `share`, `minimum`, `counted`,
      `required`
    """

    kind: ViolationKind
    message: str
    params: Mapping[str, object] = field(default_factory=dict, compare=False)


def staff_percentage(signed: Roster) -> Fraction:
    """Fulltime staff among ALL signed PhDs, so uncounted (and unaccepted) ones lower it."""
    return percent_of(signed.fulltime_staff, signed.phds + signed.unaccepted_phds)


def staff_shortage(faculty: ChapterFaculty, signed: Roster) -> tuple[int, int]:
    """(staff, required): the fulltime staff signed, and the fewest the minimum % needs."""
    phds = signed.phds + signed.unaccepted_phds

    required = round_count(
        phds * as_fraction(faculty.min_staff_percentage) / 100, faculty.staff_rounding
    )

    return signed.fulltime_staff, required


def staff_violations(faculty: ChapterFaculty, signed: Roster) -> list[Violation]:
    """Fulltime staff below `min_staff_percentage` of the signed PhDs."""
    staff, required = staff_shortage(faculty, signed)

    if staff >= required:
        return []

    percentage = staff_percentage(signed)

    message = (
        f"{faculty.name}: staff are {float(percentage):.1f}% of PhDs, "
        f"minimum is {faculty.min_staff_percentage}% ({required} staff)"
    )

    params = {
        "faculty": faculty.name,
        "percentage": percentage,
        "minimum": faculty.min_staff_percentage,
        "staff": staff,
        "required": required,
    }

    return [Violation(ViolationKind.STAFF_RATIO_TOO_LOW, message, params)]


def current_students_violations(faculty: ChapterFaculty, capacity: int) -> list[Violation]:
    """More students enrolled now than the faculty may take."""
    if faculty.current_students is None or faculty.current_students <= capacity:
        return []

    message = (
        f"{faculty.name}: {faculty.current_students} current students, "
        f"but the capacity is {capacity}"
    )

    params = {
        "faculty": faculty.name,
        "current_students": faculty.current_students,
        "capacity": capacity,
    }

    return [Violation(ViolationKind.CURRENT_STUDENTS_OVER_CAPACITY, message, params)]


def teacher_shortages(faculty: ChapterFaculty, counted: Roster) -> dict[str, tuple[int, int]]:
    """Specializations below their min_teachers: name -> (counted, minimum).

    Teachers are heads (PhDs and masters). Unlike the shares (percentages of whoever is
    there), a minimum is absolute: an empty faculty misses it too.
    """
    shortages: dict[str, tuple[int, int]] = {}

    for share in faculty.shares:
        heads = counted.of(share.specialization).heads

        if share.min_teachers is not None and heads < share.min_teachers:
            shortages[share.specialization.name] = (heads, share.min_teachers)

    return shortages


def teacher_violations(faculty: ChapterFaculty, counted: Roster) -> list[Violation]:
    """Report every specialization with fewer counted teachers than its min_teachers."""
    return [
        Violation(
            ViolationKind.TOO_FEW_TEACHERS,
            f"{faculty.name}: {name} has {heads} counted teacher(s), minimum is {minimum}",
            {
                "faculty": faculty.name,
                "specialization": name,
                "counted": heads,
                "minimum": minimum,
            },
        )
        for name, (heads, minimum) in teacher_shortages(faculty, counted).items()
    ]


def type_shortages(
    faculty: ChapterFaculty, counted: Roster
) -> dict[SpecializationType, tuple[int, int]]:
    """Types below the faculty's min specialized / supported PhDs: type -> (counted, minimum).

    Absolute, like min_teachers: an empty faculty misses it too.
    """
    shortages: dict[SpecializationType, tuple[int, int]] = {}

    for kind in SpecializationType:
        minimum, _ = faculty.teachers_of_type(kind)

        phds = sum(
            item.phds for item in counted.counts if faculty.type_of(item.specialization) is kind
        )

        if minimum is not None and phds < minimum:
            shortages[kind] = (phds, minimum)

    return shortages


def type_violations(faculty: ChapterFaculty, counted: Roster) -> list[Violation]:
    """Report a type (specialized / supported) with fewer counted PhDs than its minimum."""
    return [
        Violation(
            ViolationKind.TOO_FEW_OF_TYPE,
            f"{faculty.name}: {phds} counted {kind} PhD(s), minimum is {minimum}",
            {"faculty": faculty.name, "type": kind, "counted": phds, "minimum": minimum},
        )
        for kind, (phds, minimum) in type_shortages(faculty, counted).items()
    ]


def share_shortages(
    faculty: ChapterFaculty, signed: Roster, counted: Roster
) -> dict[str, tuple[int, int]]:
    """Specializations below their min share: name -> (counted, required) teachers.

    `required` is the min % of every counted teacher, rounded the faculty's way. Nothing
    is short in a faculty nobody is signed to; when someone is signed but no one is
    counted, a positive minimum needs one teacher.
    """
    if not signed.heads:
        return {}

    total = counted.heads

    shortages: dict[str, tuple[int, int]] = {}

    for share in faculty.shares:
        minimum = as_fraction(share.lower_bound)

        if total:
            required = round_count(total * minimum / 100, faculty.min_share_rounding)
        else:
            required = 1 if minimum > 0 else 0

        heads = counted.of(share.specialization).heads

        if heads < required:
            shortages[share.specialization.name] = (heads, required)

    return shortages


def share_violations(faculty: ChapterFaculty, signed: Roster, counted: Roster) -> list[Violation]:
    """A specialization below its min share of the counted teachers."""
    violations: list[Violation] = []

    for name, (heads, required) in share_shortages(faculty, signed, counted).items():
        share = percent_of(heads, counted.heads) if counted.heads else Fraction(0)

        minimum = next(s.lower_bound for s in faculty.shares if s.specialization.name == name)

        message = (
            f"{faculty.name}: {name} is {float(share):.1f}% of counted teachers, "
            f"minimum is {minimum}% ({required} teachers)"
        )

        params = {
            "faculty": faculty.name,
            "specialization": name,
            "share": share,
            "minimum": minimum,
            "counted": heads,
            "required": required,
        }

        violations.append(Violation(ViolationKind.SPECIALIZATION_SHARE_TOO_LOW, message, params))

    return violations
