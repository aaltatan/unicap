"""An employee's excluded faculties: where their contract is never counted."""

from dataclasses import replace
from fractions import Fraction

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
    Chapter,
    Contract,
    ContractStatus,
    Employee,
    Faculty,
    Strategy,
    evaluate_chapter,
    evaluate_faculty,
    optimize,
)


def barred_from(contract: Contract, *names: str) -> Contract:
    """The same contract, of an employee who cannot be counted in the faculties `names`."""
    employee = replace(contract.employee, excluded_faculties=frozenset(names))

    return replace(contract, employee=employee)


def test_an_employee_can_be_counted_anywhere_by_default() -> None:
    employee = Employee(1, "Dr. Hind", BIOLOGY)

    assert employee.excluded_faculties == frozenset()
    assert employee.can_be_counted_in(Faculty("Dentistry"))


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Dentistry", False), ("Pharmacy", False), ("Science", True)],
)
def test_an_employee_cannot_be_counted_in_an_excluded_faculty(name: str, expected: bool) -> None:  # noqa: FBT001
    employee = Employee(
        1, "Dr. Hind", BIOLOGY, excluded_faculties=frozenset({"Dentistry", "Pharmacy"})
    )

    assert employee.can_be_counted_in(Faculty(name)) is expected


def test_the_constraint_does_not_change_who_the_employee_is() -> None:
    plain = Employee(1, "Dr. Hind", BIOLOGY)
    barred = replace(plain, excluded_faculties=frozenset({"Dentistry"}))

    assert plain == barred
    assert hash(plain) == hash(barred)


@pytest.mark.parametrize("build", [fulltime_staff, fulltime_borrowed, parttime, master])
def test_a_contract_signed_to_an_excluded_faculty_is_never_counted(build: object) -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY))

    counted = [fulltime_staff(DENTISTRY), fulltime_staff(DENTISTRY)]
    barred = barred_from(build(DENTISTRY), "Dentistry")  # type: ignore[operator]

    report = evaluate_faculty(dentistry, [*counted, barred])

    assert report.statuses[barred] is ContractStatus.FACULTY_NOT_ALLOWED
    assert all(report.statuses[c] is ContractStatus.COUNTED for c in counted)
    assert report.counted.phd_equivalents == 2
    assert report.capacity == evaluate_faculty(dentistry, counted).capacity


def test_the_status_is_neither_an_overflow_nor_left_out() -> None:
    status = ContractStatus.FACULTY_NOT_ALLOWED

    assert not status.is_counted
    assert not status.is_overflow
    assert not status.is_excluded


def test_excluded_from_another_faculty_changes_nothing_here() -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY))
    contract = barred_from(fulltime_staff(DENTISTRY), "Pharmacy")

    report = evaluate_faculty(dentistry, [contract])

    assert report.statuses[contract] is ContractStatus.COUNTED


def test_a_barred_teacher_is_in_no_head_count_but_lowers_the_staff_percentage() -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))

    staff = fulltime_staff(DENTISTRY)
    barred = barred_from(fulltime_staff(DENTISTRY), "Dentistry")

    report = evaluate_faculty(dentistry, [staff, barred])

    assert report.signed.specialized_fulltime_staff == 1
    assert report.signed.phds == 1
    assert report.calculation.signed_roster.unaccepted_phds == 1
    assert report.staff_percentage == Fraction(50)  # one fulltime staff of two signed PhDs


def test_a_barred_teacher_is_no_limit_for_anyone() -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY))

    barred = barred_from(fulltime_staff(DENTISTRY), "Dentistry")
    first, second = parttime(DENTISTRY), parttime(DENTISTRY)

    # parttime PhDs are counted up to the counted fulltime ones: the barred one is not one
    report = evaluate_faculty(dentistry, [fulltime_staff(DENTISTRY), barred, first, second])

    assert report.statuses[first] is ContractStatus.COUNTED
    assert report.statuses[second] is ContractStatus.PARTTIME_OVERFLOW


def test_the_optimizer_never_signs_someone_where_they_cannot_be_counted() -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY))
    science = faculty("Science", specialized(DENTISTRY))

    barred = [barred_from(fulltime_staff(DENTISTRY, None), "Dentistry") for _ in range(4)]

    chapter = Chapter.assemble("2026", barred, faculties=(dentistry, science))

    optimized = optimize(chapter, Strategy.MAXIMIZE_STUDENTS)

    assert all(c.faculty == science.faculty for c in optimized.contracts)
    assert evaluate_chapter(optimized).faculties[0].capacity == 0


def test_the_optimizer_leaves_unsigned_who_can_be_counted_nowhere() -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY))
    contract = barred_from(fulltime_staff(DENTISTRY, None), "Dentistry")

    chapter = Chapter.assemble("2026", [contract], faculties=(dentistry,))

    [optimized] = optimize(chapter, Strategy.MAXIMIZE_STUDENTS).contracts

    assert optimized.faculty is None
