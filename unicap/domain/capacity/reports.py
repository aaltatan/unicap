"""Results of evaluating a faculty and a whole chapter."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from unicap.domain.capacity import students
from unicap.domain.capacity.calculation import Calculation
from unicap.domain.capacity.head_count import HeadCount
from unicap.domain.capacity.mix import Mix
from unicap.domain.capacity.violations import Violation
from unicap.domain.enums import ContractStatus, EmploymentType, SpecializationType, TeacherKind
from unicap.domain.models import Chapter, ChapterFaculty, Contract, Employee, Faculty
from unicap.domain.ordering import in_staff_order


@dataclass(frozen=True, slots=True)
class Slice:
    """How many counted teachers of one kind and one employment a faculty has."""

    employment: EmploymentType
    kind: TeacherKind
    count: int


@dataclass(frozen=True, slots=True)
class FacultyReport:
    """Who is counted (`statuses`, from counting) and what that allows (`calculation`)."""

    statuses: Mapping[Contract, ContractStatus]
    calculation: Calculation

    # --- the calculation's numbers ----------------------------------------------------

    @property
    def faculty(self) -> ChapterFaculty:
        """The faculty with the chapter's numbers."""
        return self.calculation.faculty

    @property
    def signed(self) -> HeadCount:
        return self.calculation.signed

    @property
    def counted(self) -> HeadCount:
        return self.calculation.counted

    @property
    def staff_percentage(self) -> Fraction:
        return self.calculation.staff_percentage

    @property
    def mix(self) -> Mix:
        """The signed teachers as percentages (specialized, fulltime, PhDs and their opposites)."""
        return self.calculation.mix

    @property
    def violations(self) -> tuple[Violation, ...]:
        return self.calculation.violations

    @property
    def teaching_capacity(self) -> int:
        """Students the counted teachers allow, before the faculty's max_students."""
        return self.calculation.teaching_capacity

    @property
    def capacity(self) -> int:
        """Students the faculty may take: the teaching capacity, capped by max_students."""
        return self.calculation.capacity

    @property
    def unused_teaching_capacity(self) -> int:
        """Teaching capacity lost above max_students: teachers who could serve elsewhere."""
        return self.calculation.unused_teaching_capacity

    @property
    def target_shortfall(self) -> int:
        """Students missing to reach target_students (0 when reached or no target)."""
        return self.calculation.target_shortfall

    @property
    def teacher_shortage(self) -> int:
        """Teachers missing to reach every min_teachers, and the min specialized / supported."""
        return self.calculation.teacher_shortage

    @property
    def seat_shortage(self) -> int:
        """Current students without a seat: how far rule 7 is from being met."""
        return self.calculation.seat_shortage

    @property
    def free_seats(self) -> int | None:
        """Capacity left for new students, or None when current_students is unknown."""
        return self.calculation.free_seats

    @property
    def is_compliant(self) -> bool:
        return self.calculation.is_compliant

    # --- who is counted ---------------------------------------------------------------

    @property
    def included(self) -> tuple[Contract, ...]:
        """Contracts taking part in the calculation (inactive and excluded left out)."""
        return tuple(c for c, s in self.statuses.items() if not s.is_excluded)

    @property
    def excluded(self) -> tuple[Contract, ...]:
        return tuple(c for c, s in self.statuses.items() if s.is_excluded)

    @property
    def inactive(self) -> tuple[Contract, ...]:
        return tuple(c for c, s in self.statuses.items() if s is ContractStatus.INACTIVE)

    @property
    def counted_contracts(self) -> tuple[Contract, ...]:
        return tuple(c for c, s in self.statuses.items() if s.is_counted)

    @property
    def uncounted(self) -> tuple[Contract, ...]:
        """Included contracts the ministry does not count."""
        return tuple(c for c in self.included if not self.statuses[c].is_counted)

    @property
    def overflowing(self) -> tuple[Contract, ...]:
        return tuple(c for c, status in self.statuses.items() if status.is_overflow)

    @property
    def overflowing_phds(self) -> tuple[Contract, ...]:
        return tuple(c for c in self.overflowing if c.is_phd)

    @property
    def in_staff_order(self) -> tuple[tuple[Contract, ContractStatus], ...]:
        """Every contract and its status, in staff order (see `unicap.domain.ordering`)."""
        contracts = in_staff_order(self.statuses, self.faculty.faculty)

        return tuple((contract, self.statuses[contract]) for contract in contracts)

    @property
    def composition(self) -> tuple[Slice, ...]:
        """The counted teachers by employment (staff first), then kind; empty slices left out."""
        kinds = Counter(
            (contract.employment_type, self._kind_of(contract))
            for contract in self.counted_contracts
        )

        return tuple(
            Slice(employment, kind, kinds[employment, kind])
            for employment in EmploymentType
            for kind in TeacherKind
            if kinds[employment, kind]
        )

    def _kind_of(self, contract: Contract) -> TeacherKind:
        if not contract.is_phd:
            return TeacherKind.MASTER

        specialized = (
            self.faculty.type_of(contract.employee.specialization) is SpecializationType.SPECIALIZED
        )

        if contract.is_fulltime:
            return (
                TeacherKind.SPECIALIZED_FULLTIME if specialized else TeacherKind.SUPPORTED_FULLTIME
            )

        return TeacherKind.SPECIALIZED_PARTTIME if specialized else TeacherKind.SUPPORTED_PARTTIME


@dataclass(frozen=True, slots=True)
class ChapterReport:
    chapter: Chapter
    faculties: tuple[FacultyReport, ...]

    @property
    def teaching_capacity(self) -> int:
        return sum(report.teaching_capacity for report in self.faculties)

    @property
    def faculties_capacity(self) -> int:
        """The faculties' capacities summed, before the chapter's max_students."""
        return sum(report.capacity for report in self.faculties)

    @property
    def capacity(self) -> int:
        """Students the university may take in this chapter."""
        return students.capped(self.faculties_capacity, self.chapter.max_students)

    @property
    def max_limit(self) -> int | None:
        """The highest max_students this chapter may have (None: no limit)."""
        return self.chapter.max_limit

    @property
    def current_students(self) -> int | None:
        """Students enrolled now in the faculties that say (None when none says)."""
        known = [f.faculty.current_students for f in self.faculties]

        if all(value is None for value in known):
            return None

        return sum(value for value in known if value is not None)

    @property
    def max_students(self) -> int | None:
        """The most students allowed: the chapter's max, else the faculties' (None: no max)."""
        if self.chapter.max_students is not None:
            return self.chapter.max_students

        return self.chapter.max_limit

    @property
    def free_seats(self) -> int | None:
        """Capacity left for new students, or None when no faculty knows its students."""
        current = self.current_students

        return None if current is None else self.capacity - current

    @property
    def seat_shortage(self) -> int:
        return sum(report.seat_shortage for report in self.faculties)

    @property
    def target_shortfall(self) -> int:
        return sum(report.target_shortfall for report in self.faculties)

    @property
    def violations(self) -> tuple[Violation, ...]:
        return tuple(v for report in self.faculties for v in report.violations)

    @property
    def is_compliant(self) -> bool:
        return all(report.is_compliant for report in self.faculties)

    @property
    def overflowing(self) -> tuple[Contract, ...]:
        return tuple(c for report in self.faculties for c in report.overflowing)

    def report_of(self, faculty: Faculty) -> FacultyReport:
        return next(report for report in self.faculties if report.faculty.faculty == faculty)

    def status_of(self, employee: Employee) -> ContractStatus | None:
        """Card color for the board: counted -> green, anything else -> red, None -> unsigned."""
        contract = self.chapter.contract_of(employee)

        if contract is None or contract.faculty is None:
            return None

        return self.report_of(contract.faculty).statuses[contract]
