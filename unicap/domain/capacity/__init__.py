"""Ministry counting rules.

For every faculty:
  1. A contract whose specialization the faculty does not accept is never counted, nor one
     of an employee who cannot be counted in that faculty (their excluded faculties).
  2. Parttime PhDs of a type (specialized / supported) are counted up to the number
     of counted fulltime PhDs (staff + borrowed) of the same type.
  3. A specialization is counted up to its max share of all counted teachers and up to
     its max_teachers; teachers are heads: PhDs and masters alike. Masters go first,
     then parttime, then borrowed, then staff.
  4. Masters are counted up to the number of counted specialized fulltime PhDs (and, when
     the chapter says so, only in a faculty where their specialization is specialized);
     the chapter says how many masters make one PhD (2 by default) and how that rounds.
  5. Fulltime staff must be at least `min_staff_percentage` of all PhDs signed to
     the faculty (uncounted ones included, so overflow lowers the ratio).
  6. A specialization below its min share or min_teachers is reported as a violation.
  7. More current_students than the capacity is reported as a violation.
  8. Capacity = counted PhD equivalents x students_per_phd, capped by max_students;
     a chapter's capacity is its faculties' summed, capped by its own max_students.

Every max (rules 2-4, and the faculty's max specialized / supported) is applied until
none drops anyone, so all of them hold together on the counted teachers. A minimum never
drops anyone: it is a violation. Percentages of people round to whole people the
faculty's way (`ChapterFaculty.*_rounding`).

Every number here is the chapter's: rules run on `ChapterFaculty`, the faculty with
the numbers the chapter gives it.

Counting and calculation are separate steps:
  counting.py     rules 1-4: contracts -> who is counted
  roster.py       the counts as numbers, per specialization (`Roster`)
  calculation.py  rules 5-8: numbers -> capacity and violations (no contracts)
  violations.py   rules 5-7 (what breaks compliance), on numbers
  students.py     rule 8 (student numbers and ceilings)
  head_count.py   the seven head counts
  mix.py          the signed teachers as percentages (specialized, fulltime, PhDs, ...)
  reports.py      the results: FacultyReport, ChapterReport
  evaluate.py     contracts: counting, then calculation
  numbers.py      numbers only: a calculator that needs no contract
"""

from unicap.domain.capacity.calculation import Calculation, calculate
from unicap.domain.capacity.evaluate import evaluate_chapter, evaluate_faculty
from unicap.domain.capacity.head_count import HeadCount, head_count, head_count_of
from unicap.domain.capacity.mix import Mix, mix_of
from unicap.domain.capacity.numbers import (
    FacultyNumbers,
    NumbersReport,
    count_roster,
    evaluate_numbers,
)
from unicap.domain.capacity.reports import ChapterReport, FacultyReport
from unicap.domain.capacity.roster import Roster, SpecializationCount, roster_of
from unicap.domain.capacity.violations import Violation

__all__ = [
    "Calculation",
    "ChapterReport",
    "FacultyNumbers",
    "FacultyReport",
    "HeadCount",
    "Mix",
    "NumbersReport",
    "Roster",
    "SpecializationCount",
    "Violation",
    "calculate",
    "count_roster",
    "evaluate_chapter",
    "evaluate_faculty",
    "evaluate_numbers",
    "head_count",
    "head_count_of",
    "mix_of",
    "roster_of",
]
