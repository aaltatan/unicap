"""Student numbers: the ceilings on top of what the teachers allow.

  teaching capacity  counted PhD equivalents x students_per_phd
                     (PhD equivalents are whole: the masters are rounded to whole PhDs)
  capacity           the teaching capacity, capped by the faculty's max_students
  chapter capacity   the faculties' capacities summed, capped by the chapter's max_students

(A chapter's max_students cannot exceed the faculties' maximums summed: `Chapter`
checks it.)
"""

from unicap.domain.capacity.head_count import HeadCount
from unicap.domain.models import ChapterFaculty


def capped(students: int, maximum: int | None) -> int:
    return students if maximum is None else min(students, maximum)


def teaching_capacity(faculty: ChapterFaculty, counted: HeadCount) -> int:
    return counted.phd_equivalents * faculty.students_per_phd


def capacity(faculty: ChapterFaculty, counted: HeadCount) -> int:
    return capped(teaching_capacity(faculty, counted), faculty.max_students)
