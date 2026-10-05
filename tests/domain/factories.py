"""Small builders so tests read like the rules they check.

    faculty("Dentistry", specialized(DENTISTRY, percentage=60), supported(BIOLOGY))

builds the faculty (what it accepts) together with a chapter's numbers for it
(a `ChapterFaculty`); contract builders take either.
"""

from dataclasses import dataclass
from itertools import count
from typing import TypeAlias

from unicap.domain import (
    ChapterFaculty,
    Contract,
    ContractType,
    Degree,
    Employee,
    EmploymentType,
    Faculty,
    Share,
    Specialization,
    SpecializationType,
)
from unicap.domain.utils import Percentage

DENTISTRY = Specialization("Dentistry")
BIOLOGY = Specialization("Biology")
MEDICINE = Specialization("Medicine")
PHARMACY = Specialization("Pharmacy")

_ids = count(1)

AnyFaculty: TypeAlias = Faculty | ChapterFaculty


@dataclass(frozen=True, slots=True)
class Accepted:
    """A specialization a faculty accepts, with its share in the chapter being built."""

    specialization_type: SpecializationType
    share: Share


def specialized(specialization: Specialization, **numbers: Percentage) -> Accepted:
    return Accepted(SpecializationType.SPECIALIZED, Share(specialization, **numbers))  # type: ignore[arg-type]


def supported(specialization: Specialization, **numbers: Percentage) -> Accepted:
    return Accepted(SpecializationType.SUPPORTED, Share(specialization, **numbers))  # type: ignore[arg-type]


def faculty(
    name: str,
    *accepted: Accepted,
    students_per_phd: int = 10,
    **numbers: Percentage | None,
) -> ChapterFaculty:
    """Build a faculty accepting `accepted`, with a chapter's numbers for it."""
    of_type = {
        kind: tuple(a.share.specialization for a in accepted if a.specialization_type is kind)
        for kind in SpecializationType
    }

    identity = Faculty(
        name,
        specialized=of_type[SpecializationType.SPECIALIZED],
        supported=of_type[SpecializationType.SUPPORTED],
    )

    return ChapterFaculty(
        identity,
        students_per_phd,
        shares=tuple(a.share for a in accepted),
        **numbers,  # type: ignore[arg-type]
    )


def identity(of: AnyFaculty | None) -> Faculty | None:
    return of.faculty if isinstance(of, ChapterFaculty) else of


def employee(specialization: Specialization) -> Employee:
    employee_id = next(_ids)

    return Employee(employee_id, f"employee-{employee_id}", specialization)


def fulltime_staff(specialization: Specialization, faculty: AnyFaculty | None = None) -> Contract:
    return Contract(
        employee(specialization), ContractType.FULLTIME, EmploymentType.STAFF, identity(faculty)
    )


def fulltime_borrowed(
    specialization: Specialization, faculty: AnyFaculty | None = None
) -> Contract:
    return Contract(
        employee(specialization), ContractType.FULLTIME, EmploymentType.BORROWED, identity(faculty)
    )


def parttime(specialization: Specialization, faculty: AnyFaculty | None = None) -> Contract:
    return Contract(
        employee(specialization), ContractType.PARTTIME, EmploymentType.BORROWED, identity(faculty)
    )


def master(specialization: Specialization, faculty: AnyFaculty | None = None) -> Contract:
    return Contract(
        employee(specialization),
        ContractType.FULLTIME,
        EmploymentType.STAFF,
        identity(faculty),
        degree=Degree.MASTER,
    )
