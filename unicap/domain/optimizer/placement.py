"""Who is placed first, and which faculties fit a contract."""

from collections.abc import Iterable

from unicap.domain.enums import SpecializationType
from unicap.domain.models import Contract, Faculty

type Target = Faculty | None  # None means unsigned


def placement_priority(contract: Contract) -> tuple[bool, bool, bool]:
    """Fulltime staff first: they unlock the parttime and masters limits."""
    return not contract.is_phd, not contract.is_fulltime, not contract.is_staff


def accepting(faculties: Iterable[Faculty], contract: Contract) -> list[Faculty]:
    """The faculties a contract can be counted in: its specialization and its employee fit."""
    employee = contract.employee

    return [
        f for f in faculties if f.accepts(employee.specialization) and employee.can_be_counted_in(f)
    ]


def specialized_in(faculties: Iterable[Faculty], contract: Contract) -> list[Faculty]:
    return [
        faculty
        for faculty in accepting(faculties, contract)
        if faculty.type_of(contract.employee.specialization) is SpecializationType.SPECIALIZED
    ]
