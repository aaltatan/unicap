"""Entry points: evaluate one faculty, or every faculty of a chapter.

Two separate steps: counting (`count_contracts`: who is counted) gives the numbers,
calculation (`calculate`: what the numbers allow) gives capacity and violations.
"""

from collections.abc import Sequence

from unicap.domain.capacity.calculation import calculate
from unicap.domain.capacity.counting import count_contracts
from unicap.domain.capacity.reports import ChapterReport, FacultyReport
from unicap.domain.capacity.roster import roster_of
from unicap.domain.models import Chapter, ChapterFaculty, Contract


def evaluate_chapter(chapter: Chapter) -> ChapterReport:
    """Every faculty of the chapter gets a report, empty ones too (zero)."""
    reports = tuple(
        evaluate_faculty(item, chapter.contracts_of(item.faculty)) for item in chapter.faculties
    )

    return ChapterReport(chapter=chapter, faculties=reports)


def evaluate_faculty(
    faculty: ChapterFaculty,
    contracts: Sequence[Contract],
) -> FacultyReport:
    statuses = count_contracts(faculty, contracts)

    signed = [c for c, status in statuses.items() if not status.is_excluded]

    counted = [c for c, status in statuses.items() if status.is_counted]

    calculation = calculate(
        faculty,
        counted=roster_of(faculty, counted),
        signed=roster_of(faculty, signed),
    )

    return FacultyReport(statuses=statuses, calculation=calculation)
