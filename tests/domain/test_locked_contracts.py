"""A locked contract: once signed, it stays in its faculty."""

from dataclasses import replace

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    faculty,
    fulltime_borrowed,
    fulltime_staff,
    parttime,
    specialized,
)
from tests.domain.test_excluded_faculties import barred_from
from unicap.domain import (
    Chapter,
    ChapterFaculty,
    Contract,
    DomainError,
    ErrorCode,
    Strategy,
    evaluate_chapter,
    optimize,
    substitutes_for,
)


def locked(contract: Contract) -> Contract:
    return replace(contract, is_locked=True)


def _faculty(name: str, students_per_phd: int) -> ChapterFaculty:
    return faculty(name, specialized(DENTISTRY), students_per_phd=students_per_phd)


class TestLock:
    def test_a_contract_is_not_locked_by_default(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(DENTISTRY, dentistry)

        assert not contract.is_locked
        assert not contract.is_pinned
        assert contract.can_move_to(None)

    def test_locked_and_signed_it_stays(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        contract = locked(fulltime_staff(BIOLOGY, dentistry))

        assert contract.is_pinned
        assert contract.can_move_to(dentistry.faculty)
        assert not contract.can_move_to(pharmacy.faculty)
        assert not contract.can_move_to(None)

    def test_locked_but_unsigned_it_can_still_be_signed(self, dentistry: ChapterFaculty) -> None:
        contract = locked(fulltime_staff(DENTISTRY))

        assert not contract.is_pinned
        assert contract.can_move_to(dentistry.faculty)

    @pytest.mark.parametrize("to_pharmacy", [True, False])
    def test_the_chapter_refuses_to_move_it(
        self,
        dentistry: ChapterFaculty,
        pharmacy: ChapterFaculty,
        to_pharmacy: bool,  # noqa: FBT001
    ) -> None:
        contract = locked(fulltime_staff(BIOLOGY, dentistry))

        chapter = Chapter.assemble("2026", [contract], faculties=(dentistry, pharmacy))

        with pytest.raises(DomainError, match="locked to Dentistry") as error:
            chapter.move(contract.employee, pharmacy.faculty if to_pharmacy else None)

        assert error.value.code is ErrorCode.CONTRACT_LOCKED
        assert error.value.params == {"employee": contract.employee.name, "faculty": "Dentistry"}

    def test_the_chapter_signs_a_locked_unsigned_contract(self, dentistry: ChapterFaculty) -> None:
        contract = locked(fulltime_staff(DENTISTRY))

        chapter = Chapter.assemble("2026", [contract], faculties=(dentistry,))

        signed = chapter.move(contract.employee, dentistry.faculty)

        assert signed.contracts[0].faculty == dentistry.faculty


class TestOptimizer:
    @pytest.mark.parametrize("strategy", list(Strategy))
    def test_a_locked_contract_is_never_moved(self, strategy: Strategy) -> None:
        poor, rich = _faculty("Poor", 10), _faculty("Rich", 30)

        stays, free = locked(fulltime_staff(DENTISTRY, poor)), fulltime_staff(DENTISTRY, poor)

        chapter = Chapter.assemble("2026", [stays, free], faculties=(poor, rich))

        optimized = optimize(chapter, strategy)

        assert optimized.contract_of(stays.employee).faculty == poor.faculty  # type: ignore[union-attr]

    def test_the_others_still_move_around_it(self) -> None:
        poor, rich = _faculty("Poor", 10), _faculty("Rich", 30)

        stays, free = locked(fulltime_staff(DENTISTRY, poor)), fulltime_staff(DENTISTRY, poor)

        chapter = Chapter.assemble("2026", [stays, free], faculties=(poor, rich))

        optimized = optimize(chapter)

        assert optimized.contract_of(free.employee).faculty == rich.faculty  # type: ignore[union-attr]
        assert evaluate_chapter(optimized).capacity == 40

    def test_a_locked_contract_is_not_unsigned_even_when_it_is_not_counted(self) -> None:
        dentistry = _faculty("Dentistry", 10)

        # a parttime PhD alone overflows: unlocked, the optimizer would unsign it
        alone = locked(parttime(DENTISTRY, dentistry))

        chapter = Chapter.assemble("2026", [alone], faculties=(dentistry,))

        assert optimize(chapter).unsigned == ()

    def test_a_locked_unsigned_contract_is_placed(self) -> None:
        poor, rich = _faculty("Poor", 10), _faculty("Rich", 30)

        waiting = locked(fulltime_staff(DENTISTRY))

        chapter = Chapter.assemble("2026", [waiting], faculties=(poor, rich))

        [optimized] = optimize(chapter).contracts

        assert optimized.faculty == rich.faculty
        assert optimized.is_locked


class TestSubstitutes:
    def test_the_same_terms_in_the_same_faculty(self, dentistry: ChapterFaculty) -> None:
        moved, twin = fulltime_staff(DENTISTRY, dentistry), fulltime_staff(DENTISTRY, dentistry)

        chapter = Chapter.assemble("2026", [moved, twin], faculties=(dentistry,))

        assert substitutes_for(chapter, moved) == (twin,)

    def test_anything_different_is_no_substitute(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        moved = fulltime_staff(BIOLOGY, dentistry)

        others = [
            fulltime_staff(DENTISTRY, dentistry),  # another specialization
            fulltime_borrowed(BIOLOGY, dentistry),  # another employment
            parttime(BIOLOGY, dentistry),  # another contract type
            fulltime_staff(BIOLOGY, pharmacy),  # another faculty
            fulltime_staff(BIOLOGY),  # unsigned
            replace(fulltime_staff(BIOLOGY, dentistry), is_active=False),  # left out
            barred_from(fulltime_staff(BIOLOGY, dentistry), "Pharmacy"),  # barred elsewhere
            locked(fulltime_staff(BIOLOGY, dentistry)),  # stays where it is
        ]

        chapter = Chapter.assemble("2026", [moved, *others], faculties=(dentistry, pharmacy))

        assert substitutes_for(chapter, moved) == ()

    def test_unsigned_twins_substitute_each_other(self, dentistry: ChapterFaculty) -> None:
        first, second, third = (fulltime_staff(DENTISTRY) for _ in range(3))

        chapter = Chapter.assemble("2026", [first, second, third], faculties=(dentistry,))

        assert substitutes_for(chapter, second) == (first, third)

    def test_moving_a_substitute_gives_the_same_numbers(self) -> None:
        poor, rich = _faculty("Poor", 10), _faculty("Rich", 30)

        moved, twin = fulltime_staff(DENTISTRY, poor), fulltime_staff(DENTISTRY, poor)

        chapter = Chapter.assemble("2026", [moved, twin], faculties=(poor, rich))

        [substitute] = substitutes_for(chapter, moved)

        one = evaluate_chapter(chapter.move(moved.employee, rich.faculty))
        other = evaluate_chapter(chapter.move(substitute.employee, rich.faculty))

        assert one.capacity == other.capacity == 40
