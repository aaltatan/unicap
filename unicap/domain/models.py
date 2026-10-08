"""The domain's values.

A `Chapter` is the aggregate: it owns its specializations, employees, faculties and
contracts, and nothing in it points outside it (chapters never share data).

A `Faculty` says only what it is: its name and the specializations it accepts
(specialized or supported). Its numbers are the chapter's: the chapter lists its
faculties as `ChapterFaculty` values (students per PhD, min staff %, student numbers)
with one `Share` per accepted specialization (percentages and teacher bounds).
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from unicap.domain.enums import (
    ContractType,
    Degree,
    EmploymentType,
    ErrorCode,
    SpecializationType,
)
from unicap.domain.rounding import RoundingMode
from unicap.domain.utils import Percentage, as_fraction


class DomainError(ValueError):
    """A broken domain rule: `str()` is its English message, `code` the rule, `params` its values.

    `code` and `params` let a user interface show the message in its own language; `params`
    name the owner (`faculty`, `specialization`, `chapter`, `employee` or `owner`), lists of
    names are `names`.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode | None = None,
        params: Mapping[str, object] | None = None,
    ) -> None:
        """Keep the English `message` as `str(error)`; `code` and `params` are optional."""
        super().__init__(message)
        self.code = code
        self.params: dict[str, object] = dict(params or {})


@dataclass(frozen=True, slots=True)
class Specialization:
    """`is_active=False` leaves every contract of this specialization out of calculations."""

    name: str
    is_active: bool = field(default=True, compare=False)


@dataclass(frozen=True, slots=True)
class Faculty:
    """A faculty and the specializations it accepts: specialized or supported.

    Its numbers are not here: each chapter sets them (`ChapterFaculty`).
    """

    name: str
    specialized: tuple[Specialization, ...] = ()
    supported: tuple[Specialization, ...] = ()

    def __post_init__(self) -> None:
        duplicated = [
            specialization.name
            for specialization, occurrences in Counter(self.specializations).items()
            if occurrences > 1
        ]
        if duplicated:
            msg = f"{self.name}: duplicated specializations {duplicated}"
            params = {"faculty": self.name, "names": duplicated}
            raise DomainError(msg, ErrorCode.DUPLICATED_SPECIALIZATIONS, params)

    @property
    def specializations(self) -> tuple[Specialization, ...]:
        """Every accepted specialization, specialized first."""
        return (*self.specialized, *self.supported)

    def accepts(self, specialization: Specialization) -> bool:
        return specialization in self.specialized or specialization in self.supported

    def type_of(self, specialization: Specialization) -> SpecializationType:
        if specialization in self.specialized:
            return SpecializationType.SPECIALIZED

        if specialization in self.supported:
            return SpecializationType.SUPPORTED

        msg = f"{self.name} does not accept {specialization.name}"
        params = {"faculty": self.name, "names": [specialization.name]}
        raise DomainError(msg, ErrorCode.NOT_ACCEPTED, params)


@dataclass(frozen=True, slots=True)
class Share:
    """An accepted specialization's share of a faculty's PhDs and its head count, in a chapter.

    Leave `percentage` as None when there is no required share (the new method: only
    specialized / supported matters). When `percentage` is given without bounds, the
    bounds default to the percentage itself (an exact share).

    `min_teachers` / `max_teachers` bound the teachers (PhDs and masters) of this
    specialization in the faculty: fewer is a violation, more are not counted.

    What of this specialization the faculty calculates:
      contract_type     only contracts of this type count here (None: any type)
      calculate_masters False: its masters are left out of this faculty
      masters_per_phd   how many of its masters make one PhD (summed over the faculty's
                        specializations, then rounded the faculty's `masters_rounding` way)
    """

    specialization: Specialization
    percentage: Percentage | None = None
    min_percentage: Percentage | None = None
    max_percentage: Percentage | None = None
    min_teachers: int | None = None
    max_teachers: int | None = None
    contract_type: ContractType | None = None
    calculate_masters: bool = True
    masters_per_phd: int = 2

    def __post_init__(self) -> None:
        name = self.specialization.name

        _check_not_negative(name, min_teachers=self.min_teachers, max_teachers=self.max_teachers)

        if self.masters_per_phd <= 0:
            msg = f"{name}: masters per PhD must be positive, not {self.masters_per_phd}"
            params = {"specialization": name, "per_phd": self.masters_per_phd}
            raise DomainError(msg, ErrorCode.MASTERS_PER_PHD_NOT_POSITIVE, params)

        if (
            self.min_teachers is not None
            and self.max_teachers is not None
            and self.min_teachers > self.max_teachers
        ):
            msg = (
                f"{name}: min teachers ({self.min_teachers}) "
                f"cannot exceed max teachers ({self.max_teachers})"
            )
            params = {
                "specialization": name,
                "minimum": self.min_teachers,
                "maximum": self.max_teachers,
            }
            raise DomainError(msg, ErrorCode.TEACHERS_MIN_ABOVE_MAX, params)

        if not 0 <= self.lower_bound <= self.upper_bound <= 100:
            msg = (
                f"{name}: bounds must satisfy "
                f"0 <= min ({self.lower_bound}) <= max ({self.upper_bound}) <= 100"
            )
            params = {
                "specialization": name,
                "minimum": self.lower_bound,
                "maximum": self.upper_bound,
            }
            raise DomainError(msg, ErrorCode.SHARE_BOUNDS, params)

        if self.percentage is not None and not (
            self.lower_bound <= self.percentage <= self.upper_bound
        ):
            msg = (
                f"{name}: percentage {self.percentage} is outside "
                f"[{self.lower_bound}, {self.upper_bound}]"
            )
            params = {
                "specialization": name,
                "percentage": self.percentage,
                "minimum": self.lower_bound,
                "maximum": self.upper_bound,
            }
            raise DomainError(msg, ErrorCode.PERCENTAGE_OUT_OF_BOUNDS, params)

    def allows(self, contract_type: ContractType) -> bool:
        """Whether contracts of this type count for the specialization here."""
        return self.contract_type is None or self.contract_type is contract_type

    @property
    def lower_bound(self) -> Percentage:
        return self._first_given(self.min_percentage, self.percentage, default=0)

    @property
    def upper_bound(self) -> Percentage:
        return self._first_given(self.max_percentage, self.percentage, default=100)

    def _first_given(self, *values: Percentage | None, default: Percentage) -> Percentage:
        return next((value for value in values if value is not None), default)


@dataclass(frozen=True, slots=True)
class ChapterFaculty:
    """A faculty in one chapter, with the numbers it works with there.

    The optional student numbers take part in the calculation:
      max_students      a ceiling: capacity beyond it is unused teaching capacity
      target_students   the intake the university aims for
      current_students  enrolled now: more than the capacity is a violation

    `min_specialized` / `max_specialized` (and `min_supported` / `max_supported`) bound
    the faculty's counted PhDs of that type: fewer is a violation, more are not counted.

    `shares` always ends up with one `Share` per accepted specialization, in the
    faculty's order: one not given has no share and no teacher bounds.

    A percentage of people is rounded to whole people, each its own way:
      max_share_rounding  a share's max %: the most teachers it may count (default down)
      min_share_rounding  a share's min %: the fewest it needs (default up)
      staff_rounding      min_staff_percentage: the fewest fulltime staff (default up)
      masters_rounding    its masters in whole PhDs (default down: 3 masters, 2 a PhD -> 1)
    """

    faculty: Faculty
    students_per_phd: int
    min_staff_percentage: Percentage = 50
    current_students: int | None = None
    target_students: int | None = None
    max_students: int | None = None
    shares: tuple[Share, ...] = ()
    min_specialized: int | None = None
    max_specialized: int | None = None
    min_supported: int | None = None
    max_supported: int | None = None
    max_share_rounding: RoundingMode = RoundingMode.FLOOR
    min_share_rounding: RoundingMode = RoundingMode.CEILING
    staff_rounding: RoundingMode = RoundingMode.CEILING
    masters_rounding: RoundingMode = RoundingMode.FLOOR

    def __post_init__(self) -> None:
        name = self.faculty.name

        if self.students_per_phd <= 0:
            msg = f"{name}: students per PhD must be positive"
            raise DomainError(msg, ErrorCode.STUDENTS_PER_PHD_NOT_POSITIVE, {"faculty": name})

        _check_not_negative(
            name,
            current_students=self.current_students,
            target_students=self.target_students,
            max_students=self.max_students,
            min_specialized=self.min_specialized,
            max_specialized=self.max_specialized,
            min_supported=self.min_supported,
            max_supported=self.max_supported,
        )

        for kind in SpecializationType:
            low, high = self.teachers_of_type(kind)

            if low is not None and high is not None and low > high:
                msg = f"{name}: min {kind} PhDs ({low}) cannot exceed max {kind} PhDs ({high})"
                params = {"faculty": name, "type": kind, "minimum": low, "maximum": high}
                raise DomainError(msg, ErrorCode.TYPE_MIN_ABOVE_MAX, params)

        if (
            self.target_students is not None
            and self.max_students is not None
            and self.target_students > self.max_students
        ):
            msg = (
                f"{name}: target students ({self.target_students}) "
                f"cannot exceed max students ({self.max_students})"
            )
            params = {
                "faculty": name,
                "target": self.target_students,
                "maximum": self.max_students,
            }
            raise DomainError(msg, ErrorCode.TARGET_ABOVE_MAX, params)

        given = Counter(share.specialization for share in self.shares)

        duplicated = [s.name for s, occurrences in given.items() if occurrences > 1]
        if duplicated:
            msg = f"{name}: duplicated shares {duplicated}"
            params = {"faculty": name, "names": duplicated}
            raise DomainError(msg, ErrorCode.DUPLICATED_SHARES, params)

        foreign = [s.name for s in given if not self.faculty.accepts(s)]
        if foreign:
            msg = f"{name} does not accept {foreign}"
            raise DomainError(msg, ErrorCode.NOT_ACCEPTED, {"faculty": name, "names": foreign})

        total = sum(
            as_fraction(share.percentage) for share in self.shares if share.percentage is not None
        )
        if total > 100:
            msg = f"{name}: specialization percentages sum to {total}% > 100%"
            params = {"faculty": name, "total": total}
            raise DomainError(msg, ErrorCode.PERCENTAGES_OVER_100, params)

        by_specialization = {share.specialization: share for share in self.shares}

        normalized = tuple(
            by_specialization.get(specialization, Share(specialization))
            for specialization in self.faculty.specializations
        )

        object.__setattr__(self, "shares", normalized)

    @property
    def name(self) -> str:
        return self.faculty.name

    def accepts(self, specialization: Specialization) -> bool:
        return self.faculty.accepts(specialization)

    def type_of(self, specialization: Specialization) -> SpecializationType:
        return self.faculty.type_of(specialization)

    def teachers_of_type(self, kind: SpecializationType) -> tuple[int | None, int | None]:
        """(min, max) counted PhDs of specialized or supported specializations."""
        if kind is SpecializationType.SPECIALIZED:
            return self.min_specialized, self.max_specialized

        return self.min_supported, self.max_supported

    def share_of(self, specialization: Specialization) -> Share:
        share = next((s for s in self.shares if s.specialization == specialization), None)

        if share is None:
            msg = f"{self.name} does not accept {specialization.name}"
            params = {"faculty": self.name, "names": [specialization.name]}
            raise DomainError(msg, ErrorCode.NOT_ACCEPTED, params)

        return share


@dataclass(frozen=True, slots=True)
class Employee:
    """`is_active=False` leaves every contract of this employee out of calculations.

    `excluded_faculties` (optional): the names of the faculties this employee cannot be
    counted in. Signed to one of them, their contract is never counted there.

    Example:
        >>> biology = Specialization("Biology")
        >>> hind = Employee(1, "Dr. Hind", biology, excluded_faculties=frozenset({"Pharmacy"}))
        >>> hind.can_be_counted_in(Faculty("Pharmacy")), hind.can_be_counted_in(Faculty("Science"))
        (False, True)
    """

    id: int
    name: str
    specialization: Specialization
    is_active: bool = field(default=True, compare=False)
    excluded_faculties: frozenset[str] = field(default=frozenset(), compare=False)

    def can_be_counted_in(self, faculty: Faculty) -> bool:
        """Whether nothing of the employee's own keeps them from being counted in `faculty`."""
        return faculty.name not in self.excluded_faculties


@dataclass(frozen=True, slots=True)
class Contract:
    """Employment terms of one employee in one chapter.

    `faculty=None` means unsigned. The degree belongs to the contract, so the same person
    can be counted as a master in one chapter and as a PhD in a later one.

    `is_locked` (optional): once signed, the contract stays in its faculty: it is neither
    moved to another one nor unsigned. Unsigned, a locked contract can still be signed.

    Example:
        >>> science, pharmacy = Faculty("Science"), Faculty("Pharmacy")
        >>> hind = Employee(1, "Dr. Hind", Specialization("Biology"))
        >>> contract = Contract(
        ...     hind, ContractType.FULLTIME, EmploymentType.STAFF, science, is_locked=True
        ... )
        >>> contract.can_move_to(pharmacy), contract.can_move_to(science)
        (False, True)
    """

    employee: Employee
    contract_type: ContractType
    employment_type: EmploymentType
    faculty: Faculty | None = None
    degree: Degree = Degree.PHD
    is_active: bool = True
    is_locked: bool = False

    def __post_init__(self) -> None:
        if (
            self.contract_type is ContractType.PARTTIME
            and self.employment_type is EmploymentType.STAFF
        ):
            msg = f"{self.employee.name}: a parttime contract is always borrowed"
            params = {"employee": self.employee.name}
            raise DomainError(msg, ErrorCode.PARTTIME_NOT_BORROWED, params)

    @property
    def is_phd(self) -> bool:
        return self.degree is Degree.PHD

    @property
    def is_included(self) -> bool:
        """Calculated only when the contract, its employee and specialization are active."""
        return self.is_active and self.employee.is_active and self.employee.specialization.is_active

    @property
    def is_fulltime(self) -> bool:
        return self.contract_type is ContractType.FULLTIME

    @property
    def is_staff(self) -> bool:
        return self.employment_type is EmploymentType.STAFF

    @property
    def is_signed(self) -> bool:
        return self.faculty is not None

    @property
    def is_pinned(self) -> bool:
        """Locked and signed: it stays in the faculty it is signed to."""
        return self.is_locked and self.is_signed

    def can_move_to(self, faculty: Faculty | None) -> bool:
        """Whether the contract may be signed to `faculty` (None: unsigned) from where it is."""
        return not self.is_pinned or faculty == self.faculty

    def signed_to(self, faculty: Faculty | None) -> "Contract":
        return replace(self, faculty=faculty)


@dataclass(frozen=True, slots=True)
class Chapter:
    """One chapter of a university, holding all of its own data.

    A chapter owns its specializations, employees, faculties (with their numbers) and
    contracts; nothing in it points outside it. Two chapters never share data: a
    duplicated chapter is a full copy.

    - every employee's specialization is one of the chapter's specializations
    - every faculty accepts only the chapter's specializations
    - every contract is for one of the chapter's employees (at most one each), signed to
      one of the chapter's faculties or unsigned
    - max_students cannot exceed the faculties' max_students summed (no limit while a
      faculty has no maximum)

    `Chapter.assemble` builds one from its faculties and contracts, gathering the
    specializations and employees they use.
    """

    name: str
    contracts: tuple[Contract, ...] = ()
    max_students: int | None = None
    faculties: tuple[ChapterFaculty, ...] = ()
    specializations: tuple[Specialization, ...] = ()
    employees: tuple[Employee, ...] = ()

    def __post_init__(self) -> None:
        _check_not_negative(self.name, max_students=self.max_students)

        self._check_unique()

        self._check_ownership()

        limit = self.max_limit

        if self.max_students is not None and limit is not None and self.max_students > limit:
            msg = (
                f"{self.name}: max students ({self.max_students}) cannot exceed "
                f"the faculties' limit ({limit})"
            )
            params = {"chapter": self.name, "max_students": self.max_students, "limit": limit}
            raise DomainError(msg, ErrorCode.MAX_STUDENTS_ABOVE_LIMIT, params)

    def _check_unique(self) -> None:
        for what, code, names in (
            (
                "specializations",
                ErrorCode.SPECIALIZATIONS_REPEATED,
                [s.name for s in self.specializations],
            ),
            ("employees", ErrorCode.EMPLOYEES_REPEATED, [e.id for e in self.employees]),
            ("faculties", ErrorCode.FACULTIES_REPEATED, [f.name for f in self.faculties]),
        ):
            repeated = sorted(str(name) for name, n in Counter(names).items() if n > 1)
            if repeated:
                msg = f"{self.name}: {what} listed more than once {repeated}"
                raise DomainError(msg, code, {"chapter": self.name, "names": repeated})

        repeated = sorted(
            employee.name
            for employee, n in Counter(c.employee for c in self.contracts).items()
            if n > 1
        )
        if repeated:
            msg = f"{self.name}: employees with more than one contract {repeated}"
            params = {"chapter": self.name, "names": repeated}
            raise DomainError(msg, ErrorCode.MANY_CONTRACTS, params)

    def _check_ownership(self) -> None:
        """Nothing in the chapter may point outside it."""
        specializations = set(self.specializations)

        employees = set(self.employees)

        faculties = {item.faculty for item in self.faculties}

        problems = {
            (
                ErrorCode.FOREIGN_EMPLOYEE_SPECIALIZATIONS,
                "employees of specializations not in this chapter",
            ): [e.name for e in self.employees if e.specialization not in specializations],
            (
                ErrorCode.FOREIGN_FACULTY_SPECIALIZATIONS,
                "faculties accepting specializations not in this chapter",
            ): [
                f.name
                for f in faculties
                if any(s not in specializations for s in f.specializations)
            ],
            (
                ErrorCode.FOREIGN_CONTRACT_EMPLOYEES,
                "contracts of employees not in this chapter",
            ): [c.employee.name for c in self.contracts if c.employee not in employees],
            (
                ErrorCode.FOREIGN_CONTRACT_FACULTIES,
                "contracts signed to faculties not in this chapter",
            ): [c.faculty.name for c in self.contracts if c.faculty and c.faculty not in faculties],
        }

        for (code, problem), names in problems.items():
            if names:
                msg = f"{self.name}: {problem} {sorted(set(names))}"
                raise DomainError(msg, code, {"chapter": self.name, "names": sorted(set(names))})

    @classmethod
    def assemble(  # noqa: PLR0913 - Chapter's own fields, in its order
        cls,
        name: str,
        contracts: Iterable[Contract] = (),
        max_students: int | None = None,
        faculties: Iterable[ChapterFaculty] = (),
        specializations: Iterable[Specialization] = (),
        employees: Iterable[Employee] = (),
    ) -> "Chapter":
        """Build a chapter, adding the specializations and employees its parts use.

        Given specializations and employees come first (unused ones are kept), then those
        of the faculties, the contracts' employees and their specializations.
        """
        contracts = tuple(contracts)

        faculties = tuple(faculties)

        employees = tuple(dict.fromkeys((*employees, *(c.employee for c in contracts))))

        specializations = tuple(
            dict.fromkeys(
                (
                    *specializations,
                    *(s for f in faculties for s in f.faculty.specializations),
                    *(e.specialization for e in employees),
                )
            )
        )

        return cls(
            name,
            contracts,
            max_students,
            faculties,
            specializations,
            employees,
        )

    @property
    def max_limit(self) -> int | None:
        """The highest max_students this chapter may have (None: no limit)."""
        maximums = [item.max_students for item in self.faculties]

        if not maximums or None in maximums:
            return None

        return sum(m for m in maximums if m is not None)

    @property
    def unsigned(self) -> tuple[Contract, ...]:
        return self.contracts_of(None)

    def find_faculty(self, faculty: Faculty) -> ChapterFaculty | None:
        return next((item for item in self.faculties if item.faculty == faculty), None)

    def faculty(self, faculty: Faculty) -> ChapterFaculty:
        """Return the faculty with this chapter's numbers."""
        if (item := self.find_faculty(faculty)) is None:
            msg = f"{self.name}: {faculty.name} is not in this chapter"
            params = {"chapter": self.name, "faculty": faculty.name}
            raise DomainError(msg, ErrorCode.FACULTY_NOT_IN_CHAPTER, params)
        return item

    def contracts_of(self, faculty: Faculty | None) -> tuple[Contract, ...]:
        return tuple(contract for contract in self.contracts if contract.faculty == faculty)

    def contract_of(self, employee: Employee) -> Contract | None:
        return next(
            (contract for contract in self.contracts if contract.employee == employee), None
        )

    def move(self, employee: Employee, faculty: Faculty | None) -> "Chapter":
        """Drag an employee's contract to a faculty (or back to unsigned with None).

        Raises:
            DomainError: the employee has no contract, or it is locked to another faculty.
        """
        if (contract := self.contract_of(employee)) is None:
            msg = f"{self.name}: {employee.name} has no contract"
            params = {"chapter": self.name, "employee": employee.name}
            raise DomainError(msg, ErrorCode.NO_CONTRACT, params)

        if not contract.can_move_to(faculty) and contract.faculty is not None:
            msg = f"{employee.name}: the contract is locked to {contract.faculty.name}"
            params = {"employee": employee.name, "faculty": contract.faculty.name}
            raise DomainError(msg, ErrorCode.CONTRACT_LOCKED, params)

        return self.with_contracts(
            contract.signed_to(faculty) if contract.employee == employee else contract
            for contract in self.contracts
        )

    def with_contracts(self, contracts: Iterable[Contract]) -> "Chapter":
        return replace(self, contracts=tuple(contracts))

    def with_faculty(self, item: ChapterFaculty) -> "Chapter":
        """Add a faculty to the chapter, or replace its numbers."""
        others = tuple(f for f in self.faculties if f.faculty != item.faculty)

        return replace(self, faculties=(*others, item))

    def without_faculty(self, faculty: Faculty) -> "Chapter":
        """Take a faculty out of the chapter; its contracts become unsigned."""
        return replace(
            self,
            faculties=tuple(f for f in self.faculties if f.faculty != faculty),
            contracts=tuple(
                c.signed_to(None) if c.faculty == faculty else c for c in self.contracts
            ),
        )


def _check_not_negative(owner: str, **numbers: int | None) -> None:
    negative = [name for name, value in numbers.items() if value is not None and value < 0]

    if negative:
        msg = f"{owner}: {', '.join(negative)} cannot be negative"
        raise DomainError(msg, ErrorCode.NEGATIVE, {"owner": owner, "fields": negative})
