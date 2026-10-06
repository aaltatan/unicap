"""What the university could sign: a kind of contract, of a specialization, in a faculty."""

from dataclasses import dataclass
from enum import StrEnum, auto

from unicap.domain.enums import ContractType, Degree, EmploymentType
from unicap.domain.models import Contract, Employee, Faculty, Specialization


class HireKind(StrEnum):
    FULLTIME_STAFF = auto()
    FULLTIME_BORROWED = auto()
    PARTTIME = auto()
    MASTER = auto()

    @property
    def terms(self) -> tuple[ContractType, EmploymentType, Degree]:
        """The contract's type, employment and degree."""
        return _TERMS[self]

    def contract(self, employee: Employee, faculty: Faculty) -> Contract:
        """A new contract of this kind, signed to `faculty`."""
        contract_type, employment_type, degree = self.terms

        return Contract(employee, contract_type, employment_type, faculty, degree=degree)


ALL_KINDS = frozenset(HireKind)

_TERMS = {
    HireKind.FULLTIME_STAFF: (ContractType.FULLTIME, EmploymentType.STAFF, Degree.PHD),
    HireKind.FULLTIME_BORROWED: (ContractType.FULLTIME, EmploymentType.BORROWED, Degree.PHD),
    HireKind.PARTTIME: (ContractType.PARTTIME, EmploymentType.BORROWED, Degree.PHD),
    HireKind.MASTER: (ContractType.FULLTIME, EmploymentType.STAFF, Degree.MASTER),
}


@dataclass(frozen=True, slots=True)
class Hire:
    """`count` new contracts of `kind`, of `specialization`, signed to `faculty`."""

    faculty: Faculty
    specialization: Specialization
    kind: HireKind
    count: int
