from .backup import BackupQuerySet
from .chapter import ChapterQuerySet
from .contract import ContractQuerySet
from .employee import EmployeeQuerySet
from .faculty import FacultyQuerySet
from .faculty_specialization import FacultySpecializationQuerySet
from .report_template import ReportTemplateQuerySet
from .specialization import SpecializationQuerySet

__all__ = [
    "BackupQuerySet",
    "ChapterQuerySet",
    "ContractQuerySet",
    "EmployeeQuerySet",
    "FacultyQuerySet",
    "FacultySpecializationQuerySet",
    "ReportTemplateQuerySet",
    "SpecializationQuerySet",
]
