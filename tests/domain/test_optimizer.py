import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    MEDICINE,
    PHARMACY,
    faculty,
    fulltime_staff,
    parttime,
    specialized,
)
from unicap.domain import (
    Chapter,
    ChapterFaculty,
    Contract,
    Outcome,
    Score,
    Strategy,
    evaluate_chapter,
    optimize,
    outcome_of,
)


def _terms(contract: Contract) -> tuple[object, ...]:
    return contract.employee, contract.contract_type, contract.employment_type


class TestScoreAndOutcome:
    def test_scores_add_up(self) -> None:
        total = Score(1, 10, 2, 3, 1, 5, 4) + Score(1, 5, 1, 1, 0, 0, 1) - Score(0, 5)

        assert total == Score(2, 10, 3, 4, 1, 5, 5)

    def test_outcome_applies_the_chapter_max(self) -> None:
        outcome = Outcome.of(Score(students=300, signed=4, uncounted=1), chapter_max=250, moves=0)

        assert outcome.students == 250

        assert outcome.overflow_percentage == 25

    def test_nothing_signed_is_no_overflow(self) -> None:
        assert Outcome.of(Score(), None, 0).overflow_percentage == 0

    @pytest.mark.parametrize("strategy", list(Strategy))
    def test_every_strategy_puts_compliance_first(self, strategy: Strategy) -> None:
        compliant = Outcome(0, 10, 1, 5, 4, 90, 50, 9)

        best_at_everything_else = Outcome(1, 999, 99, 99, 0, 0, 0, 0)

        assert strategy.key(compliant) > strategy.key(best_at_everything_else)

    def test_outcome_of_counts_moves_from_the_origin(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(DENTISTRY)

        origin = Chapter.assemble("2026", (contract,), faculties=(dentistry,))

        signed = origin.move(contract.employee, dentistry.faculty)

        assert outcome_of(signed, origin).moves == 1

        assert outcome_of(signed).moves == 0


class TestOptimize:
    def test_moves_overflowing_parttime_where_it_counts(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (
                fulltime_staff(DENTISTRY, dentistry),
                fulltime_staff(BIOLOGY, dentistry),
                parttime(BIOLOGY, dentistry),
                parttime(BIOLOGY, dentistry),
                fulltime_staff(PHARMACY, pharmacy),
                fulltime_staff(BIOLOGY, pharmacy),
            ),
            faculties=(dentistry, pharmacy),
        )

        before = evaluate_chapter(chapter)
        after = evaluate_chapter(optimize(chapter))

        assert len(before.overflowing) == 1
        assert after.overflowing == ()
        assert after.capacity == 60
        assert after.is_compliant

    def test_places_unsigned_contracts(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (fulltime_staff(DENTISTRY), fulltime_staff(BIOLOGY), parttime(BIOLOGY)),
            faculties=(dentistry, pharmacy),
        )

        optimized = optimize(chapter)

        assert optimized.unsigned == ()
        assert evaluate_chapter(optimized).capacity == 30

    def test_leaves_unsigned_what_cannot_count_anywhere(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (fulltime_staff(DENTISTRY), parttime(DENTISTRY), parttime(DENTISTRY)),
            faculties=(dentistry, pharmacy),
        )

        optimized = optimize(chapter)
        report = evaluate_chapter(optimized)

        assert len(optimized.unsigned) == 1
        assert report.capacity == 20
        assert report.is_compliant

    def test_leaves_unsigned_a_specialization_no_faculty_accepts(
        self, dentistry: ChapterFaculty
    ) -> None:
        stranger = fulltime_staff(MEDICINE)

        optimized = optimize(Chapter.assemble("2026", (stranger,), faculties=(dentistry,)))

        assert optimized.unsigned == (stranger,)

    def test_builds_a_faculty_that_needs_all_its_shares_at_once(
        self, dentistry_with_shares: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (
                fulltime_staff(DENTISTRY),
                fulltime_staff(DENTISTRY),
                fulltime_staff(DENTISTRY),
                fulltime_staff(BIOLOGY),
                fulltime_staff(MEDICINE),
            ),
            faculties=(dentistry_with_shares,),
        )

        report = evaluate_chapter(optimize(chapter))

        assert report.capacity == 50
        assert report.is_compliant

    def test_never_worse_than_the_current_placement(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (
                fulltime_staff(DENTISTRY, dentistry),
                parttime(DENTISTRY, dentistry),
                fulltime_staff(BIOLOGY, pharmacy),
                parttime(BIOLOGY, dentistry),
            ),
            faculties=(dentistry, pharmacy),
        )

        before = evaluate_chapter(chapter)
        after = evaluate_chapter(optimize(chapter))

        assert after.is_compliant
        assert after.capacity >= before.capacity

    def test_keeps_employment_terms(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (fulltime_staff(DENTISTRY), parttime(BIOLOGY)),
            faculties=(dentistry, pharmacy),
        )

        optimized = optimize(chapter)

        assert list(map(_terms, optimized.contracts)) == list(map(_terms, chapter.contracts))


def _faculty(name: str, students_per_phd: int, **students: int) -> ChapterFaculty:
    """Build a faculty that accepts only Dentistry, as specialized."""
    return faculty(name, specialized(DENTISTRY), students_per_phd=students_per_phd, **students)  # type: ignore[arg-type]


def _dentists(count: int, *faculties: ChapterFaculty, max_students: int | None = None) -> Chapter:
    """Build a chapter of `count` unsigned dentists working with `faculties`."""
    contracts = tuple(fulltime_staff(DENTISTRY) for _ in range(count))

    return Chapter.assemble("2026", contracts, max_students, faculties=faculties)


class TestStrategies:
    def test_maximize_students_spreads_beyond_a_faculty_max(self) -> None:
        small, big = _faculty("Small", 25, max_students=50), _faculty("Big", 10)

        optimized = optimize(_dentists(4, small, big), Strategy.MAXIMIZE_STUDENTS)

        report = evaluate_chapter(optimized)

        # 2 in Small reach its max (50); the other 2 add 20 in Big
        assert report.capacity == 70

        assert report.report_of(small.faculty).unused_teaching_capacity == 0

    def test_the_chapter_max_caps_the_result(self) -> None:
        optimized = optimize(_dentists(5, _faculty("Dentistry", 10), max_students=30))

        assert evaluate_chapter(optimized).capacity == 30

    def test_targets_come_before_maximizing(self) -> None:
        rich, targeted = _faculty("Rich", 30), _faculty("Targeted", 10, target_students=20)

        report = evaluate_chapter(optimize(_dentists(3, rich, targeted)))

        # all three in Rich would give 90, but Targeted must reach its 20 first
        assert (report.capacity, report.target_shortfall) == (50, 0)

    @pytest.mark.parametrize("strategy", list(Strategy))
    def test_every_strategy_reaches_the_targets(self, strategy: Strategy) -> None:
        rich, targeted = _faculty("Rich", 30), _faculty("Targeted", 10, target_students=20)

        report = evaluate_chapter(optimize(_dentists(3, rich, targeted), strategy))

        assert report.target_shortfall == 0

    def test_a_target_is_more_than_seating_the_current_students(self) -> None:
        growing = _faculty("Growing", 10, current_students=10, target_students=30)

        other = _faculty("Other", 30)

        report = evaluate_chapter(optimize(_dentists(3, growing, other)))

        # one dentist seats the 10 current students; the target needs all three
        assert report.report_of(growing.faculty).capacity == 30

    @pytest.mark.parametrize("strategy", list(Strategy))
    def test_a_target_never_costs_a_violation(self, strategy: Strategy) -> None:
        targeted = _faculty("Targeted", 10, target_students=20)

        crowded = _faculty("Crowded", 10, current_students=20)

        report = evaluate_chapter(optimize(_dentists(2, targeted, crowded), strategy))

        assert report.is_compliant

        assert report.report_of(crowded.faculty).capacity == 20

    def test_teacher_usage_signs_teachers_that_add_no_students(self) -> None:
        full = _faculty("Full", 10, max_students=10)

        signed, waiting = fulltime_staff(DENTISTRY, full), fulltime_staff(DENTISTRY)

        chapter = Chapter.assemble("2026", (signed, waiting), faculties=(full,))

        by_students = optimize(chapter, Strategy.MAXIMIZE_STUDENTS)

        by_usage = optimize(chapter, Strategy.MAXIMIZE_TEACHER_USAGE)

        assert outcome_of(by_students).teachers == 1

        assert outcome_of(by_usage).teachers == 2

    def test_minimize_changes_fixes_compliance_with_few_moves(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (
                fulltime_staff(DENTISTRY, dentistry),
                parttime(DENTISTRY, dentistry),
                parttime(DENTISTRY, dentistry),
                fulltime_staff(PHARMACY, pharmacy),
                fulltime_staff(BIOLOGY, pharmacy),
                fulltime_staff(BIOLOGY),
            ),
            faculties=(dentistry, pharmacy),
        )

        fewest = optimize(chapter, Strategy.MINIMIZE_CHANGES)

        most_students = optimize(chapter, Strategy.MAXIMIZE_STUDENTS)

        assert evaluate_chapter(fewest).is_compliant

        assert outcome_of(fewest, chapter).moves == 1

        assert outcome_of(most_students, chapter).moves > 1

    def test_minimize_overflow_leaves_nothing_red(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        chapter = Chapter.assemble(
            "2026",
            (
                fulltime_staff(DENTISTRY, dentistry),
                parttime(DENTISTRY, dentistry),
                parttime(DENTISTRY, dentistry),
                parttime(BIOLOGY, dentistry),
            ),
            faculties=(dentistry, pharmacy),
        )

        optimized = optimize(chapter, Strategy.MINIMIZE_OVERFLOW)

        assert outcome_of(optimized).overflow_percentage == 0

    def test_current_students_above_capacity_push_for_more_teachers(self) -> None:
        crowded = _faculty("Crowded", 10, current_students=20)

        other = _faculty("Other", 30)

        report = evaluate_chapter(optimize(_dentists(2, crowded, other)))

        # both would give more students in Other, but Crowded needs them to be compliant
        assert report.is_compliant

        assert report.report_of(crowded.faculty).capacity == 20

    def test_a_faculty_outside_the_chapter_gets_nobody(self, dentistry: ChapterFaculty) -> None:
        chapter = Chapter.assemble("2026", (fulltime_staff(PHARMACY),), faculties=(dentistry,))

        assert optimize(chapter).unsigned == chapter.contracts  # Pharmacy is not in it
