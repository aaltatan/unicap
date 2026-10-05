"""A faculty's teachers as numbers: how many of each kind, per accepted specialization.

A `Roster` is what counting (who is counted, from contracts) hands to calculation (what
the counts allow), so the calculation never needs a contract: it can run on numbers
typed in by hand (see `unicap.domain.capacity.numbers`).

Example:
    >>> from unicap.domain.models import Specialization
    >>> biology = Specialization("Biology")
    >>> roster = Roster((SpecializationCount(biology, fulltime_staff=2, masters=1),))
    >>> roster.of(biology).heads, roster.phds, roster.masters
    (3, 2, 1)
"""

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import count

from unicap.domain.enums import ContractType, Degree, EmploymentType, ErrorCode
from unicap.domain.models import ChapterFaculty, Contract, DomainError, Employee, Specialization

# the specialization of the PhDs a faculty does not accept, when numbers become contracts
UNACCEPTED = Specialization("(not accepted)")


@dataclass(frozen=True, slots=True)
class SpecializationCount:
    """Teachers of one specialization in one faculty, by kind."""

    specialization: Specialization
    fulltime_staff: int = 0
    fulltime_borrowed: int = 0
    parttime: int = 0
    masters: int = 0

    def __post_init__(self) -> None:
        negative = [
            name
            for name in ("fulltime_staff", "fulltime_borrowed", "parttime", "masters")
            if getattr(self, name) < 0
        ]

        if negative:
            owner = self.specialization.name
            msg = f"{owner}: {', '.join(negative)} cannot be negative"
            raise DomainError(msg, ErrorCode.NEGATIVE, {"owner": owner, "fields": negative})

    @property
    def fulltime(self) -> int:
        return self.fulltime_staff + self.fulltime_borrowed

    @property
    def phds(self) -> int:
        return self.fulltime + self.parttime

    @property
    def heads(self) -> int:
        """Every teacher of the specialization: PhDs and masters, one head each."""
        return self.phds + self.masters


@dataclass(frozen=True, slots=True)
class Roster:
    """A faculty's teachers by accepted specialization.

    `unaccepted_phds`: PhDs signed to the faculty whose specialization it does not accept,
    or who cannot be counted in it (`Employee.excluded_faculties`);
    never counted, but they still lower its staff percentage.
    """

    counts: tuple[SpecializationCount, ...] = ()
    unaccepted_phds: int = 0

    def of(self, specialization: Specialization) -> SpecializationCount:
        """The specialization's numbers (zeros when it has none)."""
        return next(
            (item for item in self.counts if item.specialization == specialization),
            SpecializationCount(specialization),
        )

    @property
    def phds(self) -> int:
        return sum(item.phds for item in self.counts)

    @property
    def masters(self) -> int:
        return sum(item.masters for item in self.counts)

    @property
    def heads(self) -> int:
        return self.phds + self.masters

    @property
    def fulltime_staff(self) -> int:
        return sum(item.fulltime_staff for item in self.counts)


def roster_of(faculty: ChapterFaculty, contracts: Iterable[Contract]) -> Roster:
    """Count contracts by the faculty's accepted specializations (in the faculty's order)."""
    contracts = list(contracts)

    countable = [c for c in contracts if _is_countable(faculty, c)]

    counts = tuple(
        _count(
            specialization, [c for c in countable if c.employee.specialization == specialization]
        )
        for specialization in faculty.faculty.specializations
    )

    unaccepted = sum(1 for c in contracts if c.is_phd and not _is_countable(faculty, c))

    return Roster(counts, unaccepted)


def contracts_of(faculty: ChapterFaculty, roster: Roster) -> tuple[Contract, ...]:
    """Anonymous contracts signed to the faculty, one per teacher the roster numbers.

    They are signed in the faculty's specialization order, each specialization's fulltime
    staff first, then fulltime borrowed, parttime and masters: when a rule cannot count
    everyone, the ones signed last are the ones left out.
    """
    ids = count(1)

    def signed(
        specialization: Specialization,
        how_many: int,
        terms: tuple[ContractType, EmploymentType, Degree],
    ) -> list[Contract]:
        contract_type, employment_type, degree = terms

        return [
            Contract(
                Employee(next(ids), f"{specialization.name} {number}", specialization),
                contract_type,
                employment_type,
                faculty.faculty,
                degree=degree,
            )
            for number in range(1, how_many + 1)
        ]

    fulltime_staff = (ContractType.FULLTIME, EmploymentType.STAFF, Degree.PHD)
    fulltime_borrowed = (ContractType.FULLTIME, EmploymentType.BORROWED, Degree.PHD)
    parttime = (ContractType.PARTTIME, EmploymentType.BORROWED, Degree.PHD)
    master = (ContractType.FULLTIME, EmploymentType.STAFF, Degree.MASTER)

    contracts = [
        contract
        for item in roster.counts
        for how_many, terms in (
            (item.fulltime_staff, fulltime_staff),
            (item.fulltime_borrowed, fulltime_borrowed),
            (item.parttime, parttime),
            (item.masters, master),
        )
        for contract in signed(item.specialization, how_many, terms)
    ]

    return (*contracts, *signed(UNACCEPTED, roster.unaccepted_phds, fulltime_borrowed))


def _is_countable(faculty: ChapterFaculty, contract: Contract) -> bool:
    """The faculty accepts the specialization, and the employee can be counted in it."""
    employee = contract.employee

    return employee.can_be_counted_in(faculty.faculty) and faculty.accepts(employee.specialization)


def _count(specialization: Specialization, contracts: list[Contract]) -> SpecializationCount:
    phds = [c for c in contracts if c.is_phd]

    return SpecializationCount(
        specialization,
        fulltime_staff=sum(1 for c in phds if c.is_fulltime and c.is_staff),
        fulltime_borrowed=sum(1 for c in phds if c.is_fulltime and not c.is_staff),
        parttime=sum(1 for c in phds if not c.is_fulltime),
        masters=len(contracts) - len(phds),
    )
