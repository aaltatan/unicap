"""Salary classes, cheapest first.

    masters < supported parttime < specialized parttime
            < supported borrowed fulltime < supported staff fulltime
            < specialized borrowed fulltime < specialized staff fulltime

Only the order is known (no amounts), so strategies compare classes, most expensive
first: one fewer specialized staff fulltime beats any number of cheaper changes.
"""

from collections.abc import Iterable
from enum import IntEnum

from unicap.domain.enums import SpecializationType
from unicap.domain.models import Contract, Faculty


class SalaryClass(IntEnum):
    MASTER = 1
    SUPPORTED_PARTTIME = 2
    SPECIALIZED_PARTTIME = 3
    SUPPORTED_BORROWED_FULLTIME = 4
    SUPPORTED_STAFF_FULLTIME = 5
    SPECIALIZED_BORROWED_FULLTIME = 6
    SPECIALIZED_STAFF_FULLTIME = 7


MOST_EXPENSIVE_FIRST = tuple(sorted(SalaryClass, reverse=True))


def salary_class(faculty: Faculty, contract: Contract) -> SalaryClass:
    """Return a contract's class in the faculty it is signed to.

    A specialization the faculty does not accept is still paid; it is priced as supported.
    """
    if not contract.is_phd:
        return SalaryClass.MASTER

    specialization = contract.employee.specialization

    specialized = (
        faculty.accepts(specialization)
        and faculty.type_of(specialization) is SpecializationType.SPECIALIZED
    )

    if not contract.is_fulltime:
        return SalaryClass.SPECIALIZED_PARTTIME if specialized else SalaryClass.SUPPORTED_PARTTIME

    if specialized:
        return (
            SalaryClass.SPECIALIZED_STAFF_FULLTIME
            if contract.is_staff
            else SalaryClass.SPECIALIZED_BORROWED_FULLTIME
        )

    return (
        SalaryClass.SUPPORTED_STAFF_FULLTIME
        if contract.is_staff
        else SalaryClass.SUPPORTED_BORROWED_FULLTIME
    )


def salary_counts(faculty: Faculty, contracts: Iterable[Contract]) -> tuple[int, ...]:
    """How many contracts of each class, most expensive class first."""
    classes = [salary_class(faculty, contract) for contract in contracts]

    return tuple(classes.count(salary) for salary in MOST_EXPENSIVE_FIRST)
