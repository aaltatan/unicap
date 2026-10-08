from enum import StrEnum, auto


class SpecializationType(StrEnum):
    SPECIALIZED = auto()
    SUPPORTED = auto()


class Degree(StrEnum):
    PHD = auto()
    MASTER = auto()


class ContractType(StrEnum):
    FULLTIME = auto()
    PARTTIME = auto()


class EmploymentType(StrEnum):
    STAFF = auto()
    BORROWED = auto()


class ContractStatus(StrEnum):
    """Why a signed contract is (or is not) counted by the ministry."""

    COUNTED = auto()
    SPECIALIZATION_NOT_ALLOWED = auto()
    PARTTIME_OVERFLOW = auto()
    MASTERS_OVERFLOW = auto()
    SHARE_OVERFLOW = auto()
    TEACHERS_OVERFLOW = auto()
    TYPE_OVERFLOW = auto()
    INACTIVE = auto()
    MASTERS_EXCLUDED = auto()
    CONTRACT_TYPE_NOT_ALLOWED = auto()  # its specialization counts only the other type here
    FACULTY_NOT_ALLOWED = auto()  # the employee cannot be counted in this faculty

    @property
    def is_counted(self) -> bool:
        return self is ContractStatus.COUNTED

    @property
    def is_excluded(self) -> bool:
        """Left out of the calculation: switched off, or a master its faculty row leaves out."""
        return self in (ContractStatus.INACTIVE, ContractStatus.MASTERS_EXCLUDED)

    @property
    def is_overflow(self) -> bool:
        return self in frozenset(
            {
                ContractStatus.PARTTIME_OVERFLOW,
                ContractStatus.MASTERS_OVERFLOW,
                ContractStatus.SHARE_OVERFLOW,
                ContractStatus.TEACHERS_OVERFLOW,
                ContractStatus.TYPE_OVERFLOW,
            }
        )


class ViolationKind(StrEnum):
    STAFF_RATIO_TOO_LOW = auto()
    SPECIALIZATION_SHARE_TOO_LOW = auto()
    CURRENT_STUDENTS_OVER_CAPACITY = auto()
    TOO_FEW_TEACHERS = auto()
    TOO_FEW_OF_TYPE = auto()


class ErrorCode(StrEnum):
    """Which rule a `DomainError` reports; its `params` hold the values (see `DomainError`)."""

    DUPLICATED_SPECIALIZATIONS = auto()
    NOT_ACCEPTED = auto()
    TEACHERS_MIN_ABOVE_MAX = auto()
    SHARE_BOUNDS = auto()
    PERCENTAGE_OUT_OF_BOUNDS = auto()
    STUDENTS_PER_PHD_NOT_POSITIVE = auto()
    TYPE_MIN_ABOVE_MAX = auto()
    TARGET_ABOVE_MAX = auto()
    DUPLICATED_SHARES = auto()
    PERCENTAGES_OVER_100 = auto()
    PARTTIME_NOT_BORROWED = auto()
    MAX_STUDENTS_ABOVE_LIMIT = auto()
    SPECIALIZATIONS_REPEATED = auto()
    EMPLOYEES_REPEATED = auto()
    FACULTIES_REPEATED = auto()
    MANY_CONTRACTS = auto()
    FOREIGN_EMPLOYEE_SPECIALIZATIONS = auto()
    FOREIGN_FACULTY_SPECIALIZATIONS = auto()
    FOREIGN_CONTRACT_EMPLOYEES = auto()
    FOREIGN_CONTRACT_FACULTIES = auto()
    FACULTY_NOT_IN_CHAPTER = auto()
    NO_CONTRACT = auto()
    NEGATIVE = auto()
    MASTERS_PER_PHD_NOT_POSITIVE = auto()
    CONTRACT_LOCKED = auto()


class TeacherKind(StrEnum):
    """What a counted teacher is in a faculty, besides staff / borrowed (the faculty's mix)."""

    SPECIALIZED_FULLTIME = auto()
    SUPPORTED_FULLTIME = auto()
    SPECIALIZED_PARTTIME = auto()
    SUPPORTED_PARTTIME = auto()
    MASTER = auto()
