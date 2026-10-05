"""min / max teachers, masters per row, salary classes, and the two new strategies."""

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    fulltime_borrowed,
    fulltime_staff,
    master,
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
    RoundingMode,
    SalaryClass,
    Share,
    Strategy,
    ViolationKind,
    evaluate_chapter,
    evaluate_faculty,
    optimize,
    outcome_of,
    salary_class,
)


def faculty(**teachers: int) -> ChapterFaculty:
    return build_faculty("Dentistry", specialized(DENTISTRY, **teachers), supported(BIOLOGY))


class TestTeacherLimits:
    def test_min_cannot_exceed_max(self) -> None:
        with pytest.raises(DomainError, match="min teachers"):
            Share(DENTISTRY, min_teachers=3, max_teachers=2)

    def test_teachers_beyond_the_max_are_not_counted_parttime_first(self) -> None:
        extra = parttime(DENTISTRY)

        contracts = [extra, fulltime_staff(DENTISTRY), fulltime_staff(DENTISTRY)]

        report = evaluate_faculty(faculty(max_teachers=2), contracts)

        assert report.statuses[extra] is ContractStatus.TEACHERS_OVERFLOW

        assert report.overflowing == (extra,)

        assert report.capacity == 20

    def test_fewer_than_the_min_is_a_violation(self) -> None:
        report = evaluate_faculty(faculty(min_teachers=3), [fulltime_staff(DENTISTRY)])

        assert [v.kind for v in report.violations] == [ViolationKind.TOO_FEW_TEACHERS]

        assert report.teacher_shortage == 2

    def test_an_empty_faculty_misses_its_minimum_too(self) -> None:
        report = evaluate_faculty(faculty(min_teachers=3), [])

        assert [v.kind for v in report.violations] == [ViolationKind.TOO_FEW_TEACHERS]

        assert report.teacher_shortage == 3

    def test_the_optimizer_fills_a_minimum_before_anything_else(self) -> None:
        needy = faculty(min_teachers=2)

        rich = build_faculty("Rich", specialized(DENTISTRY), students_per_phd=40)

        chapter = Chapter.assemble(
            "2026",
            (
                fulltime_staff(DENTISTRY, needy),
                fulltime_staff(DENTISTRY, rich),
                fulltime_staff(DENTISTRY, rich),
            ),
            faculties=(needy, rich),
        )

        report = evaluate_chapter(optimize(chapter))

        assert report.is_compliant

        assert report.report_of(needy.faculty).counted.phds == 2


class TestCalculateMasters:
    def test_masters_are_left_out_when_the_row_says_so(self) -> None:
        def chapter_with(*, calculate_masters: bool) -> tuple[Chapter, ChapterFaculty]:
            dentistry = build_faculty(
                "Dentistry",
                specialized(DENTISTRY, calculate_masters=calculate_masters),  # type: ignore[arg-type]
                supported(BIOLOGY),
                masters_rounding=RoundingMode.CEILING,  # type: ignore[arg-type]  # one master: one PhD
            )
            contracts = (fulltime_staff(DENTISTRY, dentistry), master(DENTISTRY, dentistry))
            return Chapter.assemble("2026", contracts, faculties=(dentistry,)), dentistry

        with_masters, _ = chapter_with(calculate_masters=True)
        without_masters, dentistry = chapter_with(calculate_masters=False)

        nabil = without_masters.contracts[1]
        without = evaluate_chapter(without_masters)

        assert (evaluate_chapter(with_masters).capacity, without.capacity) == (20, 10)
        assert without.status_of(nabil.employee) is ContractStatus.MASTERS_EXCLUDED
        assert without.report_of(dentistry.faculty).excluded == (nabil,)

    def test_the_optimizer_signs_a_master_where_masters_count(self) -> None:
        no_masters = build_faculty(
            "No masters",
            specialized(DENTISTRY, calculate_masters=False),  # type: ignore[arg-type]
        )
        with_masters = build_faculty("With masters", specialized(DENTISTRY))
        nabil = master(DENTISTRY)

        chapter = Chapter.assemble(
            "2026",
            (
                fulltime_staff(DENTISTRY, no_masters),
                fulltime_staff(DENTISTRY, with_masters),
                fulltime_staff(DENTISTRY, with_masters),
                nabil,
                master(DENTISTRY),
            ),
            faculties=(no_masters, with_masters),
        )

        optimized = optimize(chapter)

        assert optimized.contract_of(nabil.employee).faculty == with_masters.faculty


class TestSalaries:
    @pytest.mark.parametrize(
        ("contract", "specialization", "expected"),
        [
            (master, DENTISTRY, SalaryClass.MASTER),
            (parttime, BIOLOGY, SalaryClass.SUPPORTED_PARTTIME),
            (parttime, DENTISTRY, SalaryClass.SPECIALIZED_PARTTIME),
            (fulltime_borrowed, BIOLOGY, SalaryClass.SUPPORTED_BORROWED_FULLTIME),
            (fulltime_staff, BIOLOGY, SalaryClass.SUPPORTED_STAFF_FULLTIME),
            (fulltime_borrowed, DENTISTRY, SalaryClass.SPECIALIZED_BORROWED_FULLTIME),
            (fulltime_staff, DENTISTRY, SalaryClass.SPECIALIZED_STAFF_FULLTIME),
        ],
    )
    def test_salary_order(self, contract, specialization, expected: SalaryClass) -> None:  # noqa: ANN001
        assert salary_class(faculty().faculty, contract(specialization)) is expected

    def test_less_salaries_keeps_the_cheapest_team_for_the_same_students(self) -> None:
        small = build_faculty("Small", specialized(DENTISTRY), max_students=20)

        staff_1, staff_2, part = (
            fulltime_staff(DENTISTRY, small),
            fulltime_staff(DENTISTRY, small),
            parttime(DENTISTRY, small),
        )

        chapter = Chapter.assemble("2026", (staff_1, staff_2, part), faculties=(small,))

        cheap = optimize(chapter, Strategy.LESS_SALARIES)

        outcome = outcome_of(cheap)

        # 20 students either way: one staff + one parttime is cheaper than two staff
        assert outcome.students == 20

        assert cheap.contract_of(part.employee).faculty == small.faculty  # type: ignore[union-attr]

        assert len(cheap.unsigned) == 1

        assert evaluate_chapter(cheap).is_compliant


class TestBestStaffPercentage:
    def test_raises_the_weakest_faculty_first(self) -> None:
        dentistry = faculty()

        contracts = (
            fulltime_staff(DENTISTRY, dentistry),
            fulltime_borrowed(DENTISTRY, dentistry),
        )

        chapter = Chapter.assemble("2026", contracts, faculties=(dentistry,))

        before = outcome_of(chapter)

        after = outcome_of(optimize(chapter, Strategy.BEST_STAFF_PERCENTAGE))

        assert (before.lowest_staff_percentage, after.lowest_staff_percentage) == (50, 100)

        assert after.students < before.students  # the trade-off this strategy makes
