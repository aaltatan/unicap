"""Who is placed first, and which faculties fit a contract."""

from collections.abc import Iterable

from unicap.domain.enums import SpecializationType
from unicap.domain.models import Chapter, Contract, Faculty

type Target = Faculty | None  # None means unsigned


def substitutes_for(chapter: Chapter, contract: Contract) -> tuple[Contract, ...]:
    """The chapter's contracts that could make a move of `contract` in its place.

    A substitute is the same in everything a placement reads: the specialization, the
    terms (contract type, employment, degree), the faculty it is signed to now, whether it
    is calculated and the faculties its employee cannot be counted in. Moving one or the
    other gives the same numbers. A contract locked into its faculty substitutes no one.

    Example:
        >>> from unicap.domain.enums import ContractType, EmploymentType
        >>> from unicap.domain.models import Employee, Specialization
        >>> biology = Specialization("Biology")
        >>> hind, omar = (Employee(i, name, biology) for i, name in enumerate(("Hind", "Omar")))
        >>> terms = (ContractType.FULLTIME, EmploymentType.STAFF)
        >>> chapter = Chapter.assemble("2026", [Contract(hind, *terms), Contract(omar, *terms)])
        >>> [c.employee.name for c in substitutes_for(chapter, chapter.contracts[0])]
        ['Omar']
    """
    profile = _profile(contract)

    return tuple(
        other
        for other in chapter.contracts
        if other.employee != contract.employee
        and not other.is_pinned
        and _profile(other) == profile
    )


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


def _profile(contract: Contract) -> tuple[object, ...]:
    """Everything a placement reads of a contract, but who its employee is."""
    employee = contract.employee

    return (
        employee.specialization,
        contract.contract_type,
        contract.employment_type,
        contract.degree,
        contract.faculty,
        contract.is_included,
        employee.excluded_faculties,
    )
