"""Django choices for the domain's enums: same values, translated labels.

The values ARE the domain's (`SpecializationTypeChoices.SPECIALIZED == "specialized"`), so a
stored value converts back with `SpecializationType(value)`.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from unicap.domain import (
    ContractStatus,
    ContractType,
    Degree,
    EmploymentType,
    ErrorCode,
    HireKind,
    RecommendationStrategy,
    RoundingMode,
    SpecializationType,
    Strategy,
    TeacherKind,
    ViolationKind,
)


class SpecializationTypeChoices(models.TextChoices):
    """`SpecializationType`."""

    SPECIALIZED = SpecializationType.SPECIALIZED.value, _("specialized")
    SUPPORTED = SpecializationType.SUPPORTED.value, _("supported")


class DegreeChoices(models.TextChoices):
    """`Degree`."""

    PHD = Degree.PHD.value, _("PhD")
    MASTER = Degree.MASTER.value, _("master")


class ContractTypeChoices(models.TextChoices):
    """`ContractType`."""

    FULLTIME = ContractType.FULLTIME.value, _("fulltime")
    PARTTIME = ContractType.PARTTIME.value, _("parttime")


class EmploymentTypeChoices(models.TextChoices):
    """`EmploymentType`."""

    STAFF = EmploymentType.STAFF.value, _("staff")
    BORROWED = EmploymentType.BORROWED.value, _("borrowed")


class StrategyChoices(models.TextChoices):
    """`Strategy`: the optimizer's goals."""

    MAXIMIZE_STUDENTS = Strategy.MAXIMIZE_STUDENTS.value, _("maximize students")
    MAXIMIZE_TEACHER_USAGE = Strategy.MAXIMIZE_TEACHER_USAGE.value, _("maximize teacher usage")
    MINIMIZE_OVERFLOW = Strategy.MINIMIZE_OVERFLOW.value, _("minimize overflowing")
    MEET_TARGETS = Strategy.MEET_TARGETS.value, _("meet student targets")
    MINIMIZE_CHANGES = Strategy.MINIMIZE_CHANGES.value, _("fewest changes")
    MINIMIZE_TEACHERS = Strategy.MINIMIZE_TEACHERS.value, _("fewest teachers")
    LESS_SALARIES = Strategy.LESS_SALARIES.value, _("less salaries")
    BEST_STAFF_PERCENTAGE = Strategy.BEST_STAFF_PERCENTAGE.value, _("best staff percentage")


STRATEGY_DESCRIPTIONS = {
    Strategy.MAXIMIZE_STUDENTS: _("The most students the ministry allows."),
    Strategy.MAXIMIZE_TEACHER_USAGE: _("As many counted teachers as possible, as few wasted."),
    Strategy.MINIMIZE_OVERFLOW: _("The lowest share of signed contracts that are not counted."),
    Strategy.MEET_TARGETS: _("Reach every faculty's target students first, then maximize."),
    Strategy.MINIMIZE_CHANGES: _("Become compliant re-signing as few contracts as possible."),
    Strategy.MINIMIZE_TEACHERS: _("The most students with the fewest teachers: frees the rest."),
    Strategy.LESS_SALARIES: _(
        "The most students with the cheapest team: masters and parttime before fulltime, "
        "borrowed before staff, supported before specialized.",
    ),
    Strategy.BEST_STAFF_PERCENTAGE: _(
        "The highest staff share in the weakest faculty, then overall; may give up students.",
    ),
}


class RoundingChoices(models.TextChoices):
    """`RoundingMode`: how a calculated number of people rounds to whole people."""

    FLOOR = RoundingMode.FLOOR.value, _("down (floor)")
    CEILING = RoundingMode.CEILING.value, _("up (ceiling)")
    HALF_UP = RoundingMode.HALF_UP.value, _("mathematical (half up)")
    HALF_DOWN = RoundingMode.HALF_DOWN.value, _("half down")
    HALF_EVEN = RoundingMode.HALF_EVEN.value, _("half to even (banker's)")


class RecommendationStrategyChoices(models.TextChoices):
    """`RecommendationStrategy`: which helping contract the recommender signs first."""

    FEWEST_CONTRACTS = RecommendationStrategy.FEWEST_CONTRACTS.value, _("fewest contracts")
    LOW_SALARIES = RecommendationStrategy.LOW_SALARIES.value, _("low salaries")
    FULLTIME_STAFF_FIRST = (
        RecommendationStrategy.FULLTIME_STAFF_FIRST.value,
        _("fulltime staff first"),
    )
    BORROWED_FIRST = RecommendationStrategy.BORROWED_FIRST.value, _("borrowed first")
    SPECIALIZED_FIRST = RecommendationStrategy.SPECIALIZED_FIRST.value, _("specialized first")


RECOMMENDATION_STRATEGY_DESCRIPTIONS = {
    RecommendationStrategy.FEWEST_CONTRACTS: _(
        "The fewest new contracts: each one solves as much as possible.",
    ),
    RecommendationStrategy.LOW_SALARIES: _(
        "The cheapest contracts that help: masters and parttime before fulltime, "
        "borrowed before staff, supported before specialized.",
    ),
    RecommendationStrategy.FULLTIME_STAFF_FIRST: _(
        "Fulltime staff PhDs whenever they help: they raise the staff percentage too.",
    ),
    RecommendationStrategy.BORROWED_FIRST: _(
        "Fulltime borrowed PhDs whenever they help: no new permanent staff.",
    ),
    RecommendationStrategy.SPECIALIZED_FIRST: _(
        "Teachers of the faculty's own (specialized) specializations whenever they help.",
    ),
}


class HireKindChoices(models.TextChoices):
    """`HireKind`: the kinds of contract the recommender may suggest."""

    FULLTIME_STAFF = HireKind.FULLTIME_STAFF.value, _("fulltime staff PhD")
    FULLTIME_BORROWED = HireKind.FULLTIME_BORROWED.value, _("fulltime borrowed PhD")
    PARTTIME = HireKind.PARTTIME.value, _("parttime PhD")
    MASTER = HireKind.MASTER.value, _("master")


TEACHER_KIND_LABELS = {
    TeacherKind.SPECIALIZED_FULLTIME: _("specialized fulltime"),
    TeacherKind.SUPPORTED_FULLTIME: _("supported fulltime"),
    TeacherKind.SPECIALIZED_PARTTIME: _("specialized parttime"),
    TeacherKind.SUPPORTED_PARTTIME: _("supported parttime"),
    TeacherKind.MASTER: _("masters"),
}

CONTRACT_STATUS_LABELS = {
    ContractStatus.COUNTED: _("counted"),
    ContractStatus.SPECIALIZATION_NOT_ALLOWED: _("specialization not accepted here"),
    ContractStatus.PARTTIME_OVERFLOW: _("parttime beyond fulltime of its type"),
    ContractStatus.MASTERS_OVERFLOW: _("masters beyond specialized fulltime"),
    ContractStatus.SHARE_OVERFLOW: _("specialization above its max share"),
    ContractStatus.TEACHERS_OVERFLOW: _("specialization above its max teachers"),
    ContractStatus.TYPE_OVERFLOW: _("above the faculty's max of its type"),
    ContractStatus.INACTIVE: _("inactive: not calculated"),
    ContractStatus.MASTERS_EXCLUDED: _("masters of this specialization not calculated here"),
    ContractStatus.CONTRACT_TYPE_NOT_ALLOWED: _("its contract type does not count here"),
    ContractStatus.FACULTY_NOT_ALLOWED: _("the employee cannot be counted in this faculty"),
}

VIOLATION_LABELS = {
    ViolationKind.STAFF_RATIO_TOO_LOW: _("staff ratio too low"),
    ViolationKind.SPECIALIZATION_SHARE_TOO_LOW: _("specialization share too low"),
    ViolationKind.CURRENT_STUDENTS_OVER_CAPACITY: _("current students over capacity"),
    ViolationKind.TOO_FEW_TEACHERS: _("too few teachers"),
    ViolationKind.TOO_FEW_OF_TYPE: _("too few of a type"),
}


class ReportChoices(models.TextChoices):
    """The documents printed as Word / PDF files, each from its own (admin-editable) template.

    The pivots show the same numbers as small specialized / supported tables; the audit
    shows how each of them is reached.
    """

    CAPACITY = "capacity", _("capacity report")
    FACULTY_STAFF = "faculty_staff", _("faculty staff")
    CAPACITY_PIVOT = "capacity_pivot", _("capacity pivot")
    FACULTY_STAFF_PIVOT = "faculty_staff_pivot", _("faculty staff pivot")
    AUDIT = "capacity_audit", _("calculation audit")


# a violation as a translated sentence: `Violation.params` fill it (numbers already formatted)
VIOLATION_MESSAGES = {
    ViolationKind.STAFF_RATIO_TOO_LOW: _(
        "%(faculty)s: staff are %(percentage)s%% of PhDs, minimum is %(minimum)s%%",
    ),
    ViolationKind.SPECIALIZATION_SHARE_TOO_LOW: _(
        "%(faculty)s: %(specialization)s is %(share)s%% of counted teachers, "
        "minimum is %(minimum)s%%",
    ),
    ViolationKind.CURRENT_STUDENTS_OVER_CAPACITY: _(
        "%(faculty)s: %(current_students)s current students, but the capacity is %(capacity)s",
    ),
    ViolationKind.TOO_FEW_TEACHERS: _(
        "%(faculty)s: %(specialization)s has %(counted)s counted teacher(s), "
        "minimum is %(minimum)s",
    ),
    ViolationKind.TOO_FEW_OF_TYPE: _(
        "%(faculty)s: %(counted)s counted %(type)s PhD(s), minimum is %(minimum)s",
    ),
}

# a domain error as a translated sentence: `DomainError.params` fill it (`names` joined)
DOMAIN_ERROR_MESSAGES = {
    ErrorCode.DUPLICATED_SPECIALIZATIONS: _("%(faculty)s: duplicated specializations %(names)s"),
    ErrorCode.NOT_ACCEPTED: _("%(faculty)s does not accept %(names)s"),
    ErrorCode.TEACHERS_MIN_ABOVE_MAX: _(
        "%(specialization)s: min teachers (%(minimum)s) cannot exceed max teachers (%(maximum)s)",
    ),
    ErrorCode.SHARE_BOUNDS: _(
        "%(specialization)s: the min share (%(minimum)s%%) must be between 0 and "
        "the max share (%(maximum)s%%), at most 100%%",
    ),
    ErrorCode.PERCENTAGE_OUT_OF_BOUNDS: _(
        "%(specialization)s: share %(percentage)s%% is not between %(minimum)s%% and %(maximum)s%%",
    ),
    ErrorCode.STUDENTS_PER_PHD_NOT_POSITIVE: _("%(faculty)s: students per PhD must be positive"),
    ErrorCode.TYPE_MIN_ABOVE_MAX: _(
        "%(faculty)s: min %(type)s PhDs (%(minimum)s) cannot exceed max %(type)s PhDs "
        "(%(maximum)s)",
    ),
    ErrorCode.TARGET_ABOVE_MAX: _(
        "%(faculty)s: target students (%(target)s) cannot exceed max students (%(maximum)s)",
    ),
    ErrorCode.DUPLICATED_SHARES: _("%(faculty)s: duplicated shares %(names)s"),
    ErrorCode.PERCENTAGES_OVER_100: _(
        "%(faculty)s: specialization percentages sum to %(total)s%%, more than 100%%",
    ),
    ErrorCode.PARTTIME_NOT_BORROWED: _("%(employee)s: a parttime contract is always borrowed"),
    ErrorCode.MAX_STUDENTS_ABOVE_LIMIT: _(
        "%(chapter)s: max students (%(max_students)s) cannot exceed the faculties' limit "
        "(%(limit)s)",
    ),
    ErrorCode.SPECIALIZATIONS_REPEATED: _(
        "%(chapter)s: specializations listed more than once: %(names)s",
    ),
    ErrorCode.EMPLOYEES_REPEATED: _("%(chapter)s: employees listed more than once: %(names)s"),
    ErrorCode.FACULTIES_REPEATED: _("%(chapter)s: faculties listed more than once: %(names)s"),
    ErrorCode.MANY_CONTRACTS: _("%(chapter)s: employees with more than one contract: %(names)s"),
    ErrorCode.FOREIGN_EMPLOYEE_SPECIALIZATIONS: _(
        "%(chapter)s: employees of specializations not in this chapter: %(names)s",
    ),
    ErrorCode.FOREIGN_FACULTY_SPECIALIZATIONS: _(
        "%(chapter)s: faculties accepting specializations not in this chapter: %(names)s",
    ),
    ErrorCode.FOREIGN_CONTRACT_EMPLOYEES: _(
        "%(chapter)s: contracts of employees not in this chapter: %(names)s",
    ),
    ErrorCode.FOREIGN_CONTRACT_FACULTIES: _(
        "%(chapter)s: contracts signed to faculties not in this chapter: %(names)s",
    ),
    ErrorCode.FACULTY_NOT_IN_CHAPTER: _("%(chapter)s: %(faculty)s is not in this chapter"),
    ErrorCode.NO_CONTRACT: _("%(chapter)s: %(employee)s has no contract"),
    ErrorCode.NEGATIVE: _("%(owner)s: %(fields)s cannot be negative"),
    ErrorCode.MASTERS_PER_PHD_NOT_POSITIVE: _("masters per PhD must be positive"),
}

# the numbers a `NEGATIVE` error names, labelled as on the forms
FIELD_LABELS = {
    "min_teachers": _("min teachers"),
    "max_teachers": _("max teachers"),
    "current_students": _("current students"),
    "target_students": _("target students"),
    "max_students": _("max students"),
    "min_specialized": _("min specialized PhDs"),
    "max_specialized": _("max specialized PhDs"),
    "min_supported": _("min supported PhDs"),
    "max_supported": _("max supported PhDs"),
}


PER_PAGE_CHOICES = (10, 25, 50, 100, 250)


class ModalSizeChoices(models.TextChoices):
    """How wide a modal opens (resizable modals can then be dragged wider or narrower)."""

    MEDIUM = "md", _("medium")
    LARGE = "lg", _("large")
    EXTRA_LARGE = "xl", _("extra large")
    FULL = "full", _("full width")


class BackupScopeChoices(models.TextChoices):
    """What a backup holds: everything, one chapter, or one section of a chapter."""

    SYSTEM = "system", _("whole system")
    CHAPTER = "chapter", _("chapter")
    SECTION = "section", _("section")


class BackupSectionChoices(models.TextChoices):
    """The sections backed up and restored on their own (a table of a chapter)."""

    SPECIALIZATIONS = "specializations", _("specializations")
    FACULTIES = "faculties", _("faculties")
    EMPLOYEES = "employees", _("employees")
    CONTRACTS = "contracts", _("contracts")
