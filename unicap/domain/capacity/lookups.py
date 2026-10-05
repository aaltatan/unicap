"""How a faculty sees a contract: countable or not, accepted or not, specialized or supported."""

from unicap.domain.enums import SpecializationType
from unicap.domain.models import ChapterFaculty, Contract


def accepts(faculty: ChapterFaculty, contract: Contract) -> bool:
    return faculty.accepts(contract.employee.specialization)


def may_count(faculty: ChapterFaculty, contract: Contract) -> bool:
    """False when the employee cannot be counted in this faculty (`Employee.excluded_faculties`)."""
    return contract.employee.can_be_counted_in(faculty.faculty)


def type_of(faculty: ChapterFaculty, contract: Contract) -> SpecializationType:
    return faculty.type_of(contract.employee.specialization)


def is_specialized(faculty: ChapterFaculty, contract: Contract) -> bool:
    return type_of(faculty, contract) is SpecializationType.SPECIALIZED
