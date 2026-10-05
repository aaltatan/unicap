"""A faculty's min / max specialized and supported PhDs (counts, like min / max teachers)."""

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    MEDICINE,
    fulltime_borrowed,
    fulltime_staff,
    parttime,
    specialized,
    supported,
)
from tests.domain.factories import faculty as build_faculty
from unicap.domain import (
    Chapter,
    ChapterFaculty,
    ContractStatus,
    DomainError,
    ViolationKind,
    evaluate_chapter,
    evaluate_faculty,
    optimize,
)


def faculty(**limits: int) -> ChapterFaculty:
    return build_faculty(
        "Dentistry", specialized(DENTISTRY), supported(BIOLOGY), supported(MEDICINE), **limits
    )


def test_min_cannot_exceed_max() -> None:
    with pytest.raises(DomainError, match="min supported PhDs"):
        faculty(min_supported=3, max_supported=2)

    with pytest.raises(DomainError, match="cannot be negative"):
        faculty(max_specialized=-1)


def test_beyond_the_max_is_not_counted_parttime_then_borrowed_first() -> None:
    staff, borrowed, extra = fulltime_staff(BIOLOGY), fulltime_borrowed(MEDICINE), parttime(BIOLOGY)

    contracts = [fulltime_staff(DENTISTRY), fulltime_staff(DENTISTRY), extra, borrowed, staff]

    report = evaluate_faculty(faculty(max_supported=1), contracts)

    assert report.statuses[extra] is ContractStatus.TYPE_OVERFLOW

    assert report.statuses[borrowed] is ContractStatus.TYPE_OVERFLOW

    assert report.statuses[staff] is ContractStatus.COUNTED

    assert report.counted.phds == 3

    assert ContractStatus.TYPE_OVERFLOW.is_overflow


def test_the_max_is_per_type() -> None:
    contracts = [fulltime_staff(DENTISTRY), fulltime_staff(DENTISTRY), fulltime_staff(BIOLOGY)]

    report = evaluate_faculty(faculty(max_specialized=1), contracts)

    assert [s for s in report.statuses.values() if s.is_overflow] == [ContractStatus.TYPE_OVERFLOW]

    assert report.counted.phds == 2


def test_fewer_than_the_min_is_a_violation_even_when_empty() -> None:
    report = evaluate_faculty(faculty(min_specialized=2, min_supported=1), [])

    assert [v.kind for v in report.violations] == [ViolationKind.TOO_FEW_OF_TYPE] * 2

    assert report.teacher_shortage == 3

    report = evaluate_faculty(faculty(min_specialized=1), [fulltime_staff(DENTISTRY)])

    assert ViolationKind.TOO_FEW_OF_TYPE not in [v.kind for v in report.violations]


def test_the_optimizer_fills_a_minimum_first() -> None:
    needy = faculty(min_supported=1)

    rich = build_faculty("Rich", specialized(BIOLOGY), students_per_phd=40)

    chapter = Chapter.assemble(
        "2026",
        (fulltime_staff(DENTISTRY, needy), fulltime_staff(BIOLOGY, rich)),
        faculties=(needy, rich),
    )

    report = evaluate_chapter(optimize(chapter)).report_of(needy.faculty)

    assert not [v for v in report.violations if v.kind is ViolationKind.TOO_FEW_OF_TYPE]
