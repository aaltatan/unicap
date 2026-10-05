# ruff: noqa: S311 - seeded randomness generates test cases, nothing secret
"""The recommender: which contracts to sign so that every problem is solved."""

import random

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    faculty,
    fulltime_borrowed,
    fulltime_staff,
    specialized,
    supported,
)
from tests.domain.test_constraints_hold import random_contracts, random_faculty
from unicap.domain import (
    Chapter,
    ChapterReport,
    ContractType,
    HireKind,
    RecommendationStrategy,
    recommend,
)
from unicap.domain.recommender.gap import gap_of


def chapter_of(*faculties_and_contracts: object, **settings: object) -> Chapter:
    faculties = [item for item in faculties_and_contracts if not isinstance(item, list)]
    contracts = [c for item in faculties_and_contracts if isinstance(item, list) for c in item]

    return Chapter.assemble("2026", contracts, faculties=faculties, **settings)  # type: ignore[arg-type]


class TestRecommend:
    def test_a_compliant_chapter_needs_nothing(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY))

        recommendation = recommend(chapter_of(dentistry, [fulltime_staff(DENTISTRY, dentistry)]))

        assert recommendation.hires == ()
        assert recommendation.is_solved

    def test_min_teachers_are_filled(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY, min_teachers=3))

        recommendation = recommend(chapter_of(dentistry))

        assert recommendation.contracts == 3
        assert recommendation.is_solved
        assert {hire.specialization for hire in recommendation.hires} == {DENTISTRY}

    def test_current_students_get_seats(self) -> None:
        dentistry = faculty(
            "Dentistry", specialized(DENTISTRY), students_per_phd=10, current_students=35
        )

        recommendation = recommend(chapter_of(dentistry, [fulltime_staff(DENTISTRY, dentistry)]))

        assert recommendation.is_solved
        assert recommendation.after.capacity >= 35
        assert recommendation.before.capacity == 10

    def test_targets_only_when_asked(self) -> None:
        dentistry = faculty(
            "Dentistry", specialized(DENTISTRY), students_per_phd=10, target_students=30
        )

        chapter = chapter_of(dentistry, [fulltime_staff(DENTISTRY, dentistry)])

        assert recommend(chapter).contracts == 0
        assert recommend(chapter, meet_targets=True).after.target_shortfall == 0

    def test_a_low_staff_ratio_needs_staff(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY), min_staff_percentage=50)

        borrowed = [fulltime_borrowed(DENTISTRY, dentistry) for _ in range(3)]

        recommendation = recommend(chapter_of(dentistry, borrowed))

        assert recommendation.is_solved
        assert [hire.kind for hire in recommendation.hires] == [HireKind.FULLTIME_STAFF]

    @pytest.mark.parametrize(
        ("strategy", "expected"),
        [
            (RecommendationStrategy.FULLTIME_STAFF_FIRST, HireKind.FULLTIME_STAFF),
            (RecommendationStrategy.BORROWED_FIRST, HireKind.FULLTIME_BORROWED),
            (RecommendationStrategy.LOW_SALARIES, HireKind.MASTER),
        ],
    )
    def test_the_strategy_picks_the_kind(
        self, strategy: RecommendationStrategy, expected: HireKind
    ) -> None:
        dentistry = faculty(
            "Dentistry", specialized(DENTISTRY), students_per_phd=10, current_students=40
        )

        staff = [fulltime_staff(DENTISTRY, dentistry) for _ in range(3)]

        recommendation = recommend(chapter_of(dentistry, staff), strategy)

        assert recommendation.is_solved
        assert recommendation.hires[0].kind is expected

    def test_only_the_allowed_kinds(self) -> None:
        dentistry = faculty(
            "Dentistry", specialized(DENTISTRY), students_per_phd=10, current_students=40
        )

        recommendation = recommend(
            chapter_of(dentistry, [fulltime_staff(DENTISTRY, dentistry)]),
            RecommendationStrategy.LOW_SALARIES,
            kinds=frozenset({HireKind.FULLTIME_BORROWED}),
        )

        assert {hire.kind for hire in recommendation.hires} == {HireKind.FULLTIME_BORROWED}

    def test_no_masters_where_the_row_leaves_them_out(self) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY, calculate_masters=False),  # type: ignore[arg-type]
            students_per_phd=10,
            current_students=40,
        )

        recommendation = recommend(
            chapter_of(dentistry, [fulltime_staff(DENTISTRY, dentistry) for _ in range(3)]),
            RecommendationStrategy.LOW_SALARIES,
        )

        assert HireKind.MASTER not in {hire.kind for hire in recommendation.hires}

    def test_only_the_rows_contract_type(self) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY, contract_type=ContractType.PARTTIME),  # type: ignore[arg-type]
            supported(BIOLOGY),
            students_per_phd=10,
            current_students=40,
        )

        recommendation = recommend(chapter_of(dentistry))

        assert recommendation.is_solved
        for hire in recommendation.hires:
            if hire.specialization == DENTISTRY:
                assert hire.kind is HireKind.PARTTIME

    def test_specialized_first_prefers_the_faculty_specialty(self) -> None:
        dentistry = faculty(
            "Dentistry",
            supported(BIOLOGY),
            specialized(DENTISTRY),
            students_per_phd=10,
            current_students=20,
        )

        recommendation = recommend(chapter_of(dentistry), RecommendationStrategy.SPECIALIZED_FIRST)

        assert recommendation.is_solved
        assert {hire.specialization for hire in recommendation.hires} == {DENTISTRY}

    def test_what_hires_cannot_solve_is_left_unsolved(self) -> None:
        # 2 teachers at most, but 50 students need 5
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY, max_teachers=2),
            students_per_phd=10,
            current_students=50,
        )

        recommendation = recommend(chapter_of(dentistry))

        assert not recommendation.is_solved
        assert recommendation.contracts == 2


@pytest.mark.parametrize("seed", range(25))
@pytest.mark.parametrize("strategy", list(RecommendationStrategy))
def test_hires_never_leave_a_faculty_further_from_compliance(
    seed: int, strategy: RecommendationStrategy
) -> None:
    rng = random.Random(seed)
    item = random_faculty(rng)
    chapter = Chapter.assemble("2026", random_contracts(rng, item), faculties=(item,))

    recommendation = recommend(chapter, strategy, meet_targets=rng.random() > 0.5)

    def distance(report: ChapterReport) -> int:
        return gap_of(report.faculties[0], meet_targets=recommendation.meet_targets).distance

    assert distance(recommendation.after) <= distance(recommendation.before)
    assert recommendation.is_solved == (distance(recommendation.after) == 0)
