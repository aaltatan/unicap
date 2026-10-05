"""Counting and calculation apart: capacity from numbers, without a single contract."""

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    faculty,
    fulltime_borrowed,
    fulltime_staff,
    master,
    parttime,
    specialized,
    supported,
)
from unicap.domain import (
    DomainError,
    FacultyNumbers,
    Roster,
    SpecializationCount,
    ViolationKind,
    calculate,
    count_roster,
    evaluate_faculty,
    evaluate_numbers,
)


def dentistry_numbers(**counts: int) -> FacultyNumbers:
    dentistry = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))

    return FacultyNumbers(dentistry, Roster((SpecializationCount(DENTISTRY, **counts),)))


class TestNumbers:
    def test_negative_numbers_are_refused(self) -> None:
        with pytest.raises(DomainError, match="cannot be negative"):
            SpecializationCount(DENTISTRY, parttime=-1)

    def test_numbers_are_counted_by_the_same_rules_as_contracts(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))

        contracts = [
            fulltime_staff(DENTISTRY, dentistry),
            fulltime_borrowed(DENTISTRY, dentistry),
            *(parttime(DENTISTRY, dentistry) for _ in range(4)),
            *(master(DENTISTRY, dentistry) for _ in range(5)),
            parttime(BIOLOGY, dentistry),
        ]

        by_contracts = evaluate_faculty(dentistry, contracts)

        signed = Roster(
            (
                SpecializationCount(
                    DENTISTRY, fulltime_staff=1, fulltime_borrowed=1, parttime=4, masters=5
                ),
                SpecializationCount(BIOLOGY, parttime=1),
            )
        )

        counted = count_roster(dentistry, signed)

        assert counted.of(DENTISTRY) == SpecializationCount(
            DENTISTRY, fulltime_staff=1, fulltime_borrowed=1, parttime=2, masters=2
        )
        assert counted.of(BIOLOGY).heads == 0  # no supported fulltime: no supported parttime
        assert evaluate_numbers((FacultyNumbers(dentistry, signed),)).capacity == (
            by_contracts.capacity
        )

    def test_counted_numbers_are_only_calculated(self) -> None:
        numbers = dentistry_numbers(fulltime_staff=1, parttime=4)

        counted = evaluate_numbers((numbers,), count=False)
        by_rules = evaluate_numbers((numbers,))

        # taken as counted: all 5 PhDs; by the rules: 1 fulltime lets in 1 parttime
        assert (counted.capacity, by_rules.capacity) == (50, 20)

    def test_the_chapter_max_caps_the_total(self) -> None:
        numbers = dentistry_numbers(fulltime_staff=5)

        assert evaluate_numbers((numbers, numbers), max_students=70).capacity == 70

    @pytest.mark.parametrize(
        ("row", "expected"),
        [
            ({}, 50),  # 3 masters, 2 a PhD, rounded down: 1 PhD
            ({"masters_per_phd": 1}, 70),
            ({"calculate_masters": False}, 40),
        ],
    )
    def test_each_rows_masters_settings_apply(self, row: dict[str, object], expected: int) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY, **row))  # type: ignore[arg-type]
        teachers = Roster((SpecializationCount(DENTISTRY, fulltime_staff=4, masters=3),))

        assert evaluate_numbers((FacultyNumbers(dentistry, teachers),)).capacity == expected

    def test_violations_come_from_the_numbers(self) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY, min_teachers=3),
            min_staff_percentage=50,
        )

        result = calculate(
            dentistry,
            counted=Roster((SpecializationCount(DENTISTRY, fulltime_borrowed=2),)),
        )

        assert {v.kind for v in result.violations} == {
            ViolationKind.TOO_FEW_TEACHERS,
            ViolationKind.STAFF_RATIO_TOO_LOW,
        }
        assert (result.teacher_shortage, result.staff_shortage) == (1, 1)
