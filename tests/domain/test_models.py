from collections.abc import Callable

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    MEDICINE,
    employee,
    faculty,
    fulltime_borrowed,
    fulltime_staff,
    master,
    parttime,
    specialized,
    supported,
)
from unicap.domain import (
    Chapter,
    ChapterFaculty,
    Contract,
    ContractType,
    DomainError,
    EmploymentType,
    Faculty,
    Share,
    SpecializationType,
    evaluate_chapter,
)


class TestShare:
    def test_percentage_without_bounds_is_an_exact_share(self) -> None:
        share = Share(DENTISTRY, percentage=60)

        assert (share.lower_bound, share.upper_bound) == (60, 60)

    def test_no_percentage_means_no_share_constraint(self) -> None:
        share = Share(BIOLOGY)

        assert (share.lower_bound, share.upper_bound) == (0, 100)

    @pytest.mark.parametrize(
        "percentages",
        [
            {"percentage": 70, "min_percentage": 50, "max_percentage": 65},
            {"percentage": 40, "min_percentage": 50, "max_percentage": 65},
            {"min_percentage": 70, "max_percentage": 60},
            {"max_percentage": 120},
            {"min_percentage": -1},
        ],
    )
    def test_invalid_bounds_are_rejected(self, percentages: dict[str, float]) -> None:
        with pytest.raises(DomainError):
            Share(DENTISTRY, **percentages)


class TestFaculty:
    def test_a_faculty_has_no_numbers_only_what_it_accepts(self) -> None:
        dental = Faculty("Dentistry", specialized=(DENTISTRY,), supported=(BIOLOGY,))

        assert dental.specializations == (DENTISTRY, BIOLOGY)
        assert dental.type_of(BIOLOGY) is SpecializationType.SUPPORTED
        assert not dental.accepts(MEDICINE)

    def test_duplicated_specializations_are_rejected(self) -> None:
        with pytest.raises(DomainError, match="duplicated"):
            Faculty("Dentistry", specialized=(DENTISTRY,), supported=(DENTISTRY,))

    def test_type_of_rejects_a_specialization_it_does_not_accept(self) -> None:
        with pytest.raises(DomainError, match="does not accept"):
            Faculty("Dentistry", specialized=(DENTISTRY,)).type_of(MEDICINE)


class TestChapterFaculty:
    def test_percentages_over_100_are_rejected(self) -> None:
        with pytest.raises(DomainError, match="sum"):
            faculty(
                "Dentistry",
                specialized(DENTISTRY, percentage=60),
                supported(BIOLOGY, percentage=30),
                supported(MEDICINE, percentage=20),
            )

    def test_a_share_of_a_specialization_not_accepted_is_rejected(self) -> None:
        dental = Faculty("Dentistry", specialized=(DENTISTRY,))

        with pytest.raises(DomainError, match="does not accept"):
            ChapterFaculty(dental, 10, shares=(Share(MEDICINE, 20),))

    def test_every_accepted_specialization_gets_a_share(self) -> None:
        dental = Faculty("Dentistry", specialized=(DENTISTRY,), supported=(BIOLOGY,))

        numbers = ChapterFaculty(dental, 10, shares=(Share(BIOLOGY, 20),))

        assert numbers.shares == (Share(DENTISTRY), Share(BIOLOGY, 20))
        assert numbers == ChapterFaculty(dental, 10, shares=(Share(DENTISTRY), Share(BIOLOGY, 20)))

    def test_share_of_rejects_a_specialization_it_does_not_accept(
        self, dentistry: ChapterFaculty
    ) -> None:
        with pytest.raises(DomainError):
            dentistry.share_of(MEDICINE)

    def test_students_per_phd_must_be_positive(self) -> None:
        with pytest.raises(DomainError, match="positive"):
            faculty("Dentistry", students_per_phd=0)

    def test_student_numbers_are_optional(self, dentistry: ChapterFaculty) -> None:
        assert (dentistry.current_students, dentistry.target_students, dentistry.max_students) == (
            None,
            None,
            None,
        )

    @pytest.mark.parametrize(
        "numbers",
        [{"current_students": -1}, {"target_students": -5}, {"max_students": -1}],
    )
    def test_negative_numbers_are_rejected(self, numbers: dict[str, int]) -> None:
        with pytest.raises(DomainError, match="negative"):
            faculty("Dentistry", specialized(DENTISTRY), **numbers)  # type: ignore[arg-type]

    def test_target_cannot_exceed_max(self) -> None:
        with pytest.raises(DomainError, match="cannot exceed"):
            faculty("Dentistry", target_students=300, max_students=200)


class TestContract:
    def test_parttime_is_always_borrowed(self) -> None:
        with pytest.raises(DomainError, match="borrowed"):
            Contract(employee(DENTISTRY), ContractType.PARTTIME, EmploymentType.STAFF)

    def test_signed_to_changes_only_the_faculty(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(DENTISTRY)

        signed = contract.signed_to(dentistry.faculty)

        assert signed.is_signed
        assert not contract.is_signed
        assert signed.employee == contract.employee


class TestChapter:
    def test_employee_has_one_contract_per_chapter(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(DENTISTRY)

        with pytest.raises(DomainError, match="more than one contract"):
            Chapter.assemble(
                "2026", (contract, contract.signed_to(dentistry.faculty)), faculties=(dentistry,)
            )

    def test_move_signs_and_unsigns_without_mutating(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(DENTISTRY)
        chapter = Chapter.assemble("2026", (contract,), faculties=(dentistry,))

        signed = chapter.move(contract.employee, dentistry.faculty)

        assert chapter.unsigned == (contract,)
        assert signed.contracts_of(dentistry.faculty) == (contract.signed_to(dentistry.faculty),)
        assert signed.move(contract.employee, None).unsigned == (contract,)

    def test_move_rejects_an_employee_without_contract(self, dentistry: ChapterFaculty) -> None:
        with pytest.raises(DomainError, match="no contract"):
            Chapter.assemble("2026", faculties=(dentistry,)).move(
                employee(DENTISTRY), dentistry.faculty
            )

    def test_contracts_are_signed_to_the_chapter_faculties_only(
        self, dentistry: ChapterFaculty
    ) -> None:
        with pytest.raises(DomainError, match="not in this chapter"):
            Chapter.assemble("2026", (fulltime_staff(DENTISTRY, dentistry),))

    def test_a_faculty_is_listed_once(self, dentistry: ChapterFaculty) -> None:
        with pytest.raises(DomainError, match="more than once"):
            Chapter.assemble("2026", faculties=(dentistry, dentistry))

    def test_faculty_gives_the_chapter_numbers(self, dentistry: ChapterFaculty) -> None:
        chapter = Chapter.assemble("2026", faculties=(dentistry,))

        assert chapter.faculty(dentistry.faculty) is dentistry

        with pytest.raises(DomainError, match="not in this chapter"):
            chapter.faculty(Faculty("Law"))

    def test_with_and_without_faculty(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(DENTISTRY, dentistry)

        chapter = Chapter.assemble("2026", (contract,), faculties=(dentistry,))

        bigger = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY), max_students=90)

        assert chapter.with_faculty(bigger).faculties == (bigger,)

        emptied = chapter.without_faculty(dentistry.faculty)

        assert emptied.faculties == ()
        assert emptied.unsigned == (contract.signed_to(None),)

    @pytest.mark.parametrize("builder", [fulltime_staff, fulltime_borrowed, parttime, master])
    def test_contract_of(self, builder: Callable[..., Contract]) -> None:
        contract = builder(DENTISTRY)
        chapter = Chapter.assemble("2026", (contract,))

        assert chapter.contract_of(contract.employee) == contract
        assert chapter.contract_of(employee(DENTISTRY)) is None

    def test_chapter_max_cannot_be_negative(self) -> None:
        with pytest.raises(DomainError, match="negative"):
            Chapter.assemble("2026", max_students=-1)


class TestChapterOwnsItsData:
    def test_assemble_gathers_what_the_parts_use(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(MEDICINE, dentistry)

        chapter = Chapter.assemble("2026", (contract,), faculties=(dentistry,))

        assert chapter.employees == (contract.employee,)

        assert set(chapter.specializations) == {DENTISTRY, BIOLOGY, MEDICINE}

    def test_a_contract_of_an_employee_outside_the_chapter(self, dentistry: ChapterFaculty) -> None:
        contract = fulltime_staff(DENTISTRY, dentistry)

        with pytest.raises(DomainError, match="employees not in this chapter"):
            Chapter(
                "2026", (contract,), faculties=(dentistry,), specializations=(DENTISTRY, BIOLOGY)
            )

    def test_an_employee_of_a_specialization_outside_the_chapter(self) -> None:
        stranger = employee(MEDICINE)

        with pytest.raises(DomainError, match="specializations not in this chapter"):
            Chapter("2026", specializations=(DENTISTRY,), employees=(stranger,))

    def test_a_faculty_accepting_a_specialization_outside_the_chapter(
        self, dentistry: ChapterFaculty
    ) -> None:
        with pytest.raises(DomainError, match="faculties accepting"):
            Chapter("2026", faculties=(dentistry,), specializations=(DENTISTRY,))

    def test_names_are_unique_inside_a_chapter(self) -> None:
        with pytest.raises(DomainError, match="specializations listed more than once"):
            Chapter("2026", specializations=(DENTISTRY, DENTISTRY))

        clash = (
            faculty("Dentistry", specialized(DENTISTRY)),
            faculty("Dentistry", specialized(BIOLOGY)),
        )

        with pytest.raises(DomainError, match="faculties listed more than once"):
            Chapter.assemble("2026", faculties=clash)

    def test_unused_specializations_and_employees_are_kept(self) -> None:
        idle = employee(BIOLOGY)

        chapter = Chapter.assemble("2026", specializations=(MEDICINE,), employees=(idle,))

        assert chapter.specializations == (MEDICINE, BIOLOGY)

        assert chapter.employees == (idle,)


class TestNumbersPerChapter:
    def test_two_chapters_evaluate_the_same_faculty_differently(self) -> None:
        fall = faculty("Dental", specialized(DENTISTRY), max_students=100)

        spring = faculty("Dental", specialized(DENTISTRY), students_per_phd=25, max_students=200)

        assert fall.faculty == spring.faculty  # one faculty, two chapters' numbers

        def capacity(numbers: ChapterFaculty) -> int:
            contracts = tuple(fulltime_staff(DENTISTRY, numbers) for _ in range(3))

            return evaluate_chapter(Chapter.assemble("c", contracts, faculties=(numbers,))).capacity

        assert (capacity(fall), capacity(spring)) == (30, 75)
