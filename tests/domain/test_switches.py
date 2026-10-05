"""is_active switches, degree on the contract, and the MINIMIZE_TEACHERS strategy."""

from dataclasses import replace

from tests.domain.factories import (
    DENTISTRY,
    faculty,
    fulltime_staff,
    master,
    parttime,
    specialized,
)
from unicap.domain import (
    Chapter,
    ChapterFaculty,
    ContractStatus,
    Degree,
    Specialization,
    Strategy,
    evaluate_chapter,
    evaluate_faculty,
    optimize,
    outcome_of,
)


class TestInactive:
    def test_an_inactive_contract_is_not_calculated(self, dentistry: ChapterFaculty) -> None:
        active = fulltime_staff(DENTISTRY)

        inactive = replace(fulltime_staff(DENTISTRY), is_active=False)

        report = evaluate_faculty(dentistry, [active, inactive])

        assert report.statuses[inactive] is ContractStatus.INACTIVE

        assert report.capacity == 10

        assert report.inactive == (inactive,)

        assert report.uncounted == ()  # inactive is not "uncounted": it is left out

    def test_an_inactive_employee_or_specialization_leaves_its_contracts_out(
        self, dentistry: ChapterFaculty
    ) -> None:
        off = replace(
            fulltime_staff(DENTISTRY),
            employee=replace(fulltime_staff(DENTISTRY).employee, is_active=False),
        )

        sleeping = Specialization("Dentistry", is_active=False)

        asleep = fulltime_staff(sleeping)

        report = evaluate_faculty(dentistry, [off, asleep])

        assert [report.statuses[c] for c in (off, asleep)] == [ContractStatus.INACTIVE] * 2

        assert report.capacity == 0

    def test_an_inactive_specialization_is_still_the_same_specialization(self) -> None:
        assert Specialization("Dentistry", is_active=False) == DENTISTRY

    def test_inactive_parttime_does_not_lower_the_staff_ratio(
        self, dentistry: ChapterFaculty
    ) -> None:
        contracts = [
            fulltime_staff(DENTISTRY),
            replace(parttime(DENTISTRY), is_active=False),
            replace(parttime(DENTISTRY), is_active=False),
        ]

        report = evaluate_faculty(dentistry, contracts)

        assert report.staff_percentage == 100

        assert report.is_compliant

    def test_the_optimizer_leaves_inactive_contracts_where_they_are(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        parked = replace(fulltime_staff(DENTISTRY, dentistry), is_active=False)

        chapter = Chapter.assemble(
            "2026", (parked, fulltime_staff(DENTISTRY)), faculties=(dentistry, pharmacy)
        )

        optimized = optimize(chapter)

        assert optimized.contract_of(parked.employee) == parked


class TestDegreeOnTheContract:
    def test_the_same_person_can_be_a_master_then_a_phd(self, dentistry: ChapterFaculty) -> None:
        as_master = master(DENTISTRY, dentistry)

        as_phd = replace(as_master, degree=Degree.PHD)

        assert as_master.employee == as_phd.employee

        assert evaluate_faculty(dentistry, [as_master]).counted.masters == 0  # no fulltime PhD

        assert evaluate_faculty(dentistry, [as_phd]).capacity == 10


class TestMinimizeTeachers:
    def test_frees_teachers_who_add_no_student(self) -> None:
        small = faculty("Small", specialized(DENTISTRY), max_students=20)

        contracts = tuple(fulltime_staff(DENTISTRY, small) for _ in range(4))

        chapter = Chapter.assemble("2026", contracts, faculties=(small,))

        optimized = optimize(chapter, Strategy.MINIMIZE_TEACHERS)

        outcome = outcome_of(optimized)

        # two PhDs already reach the max of 20 students: the other two are freed
        assert (outcome.students, outcome.signed) == (20, 2)

        assert len(optimized.unsigned) == 2

        maximized = outcome_of(optimize(chapter, Strategy.MAXIMIZE_STUDENTS))

        assert maximized.signed == 4  # keeps them: fewer moves

        assert evaluate_chapter(optimized).is_compliant
