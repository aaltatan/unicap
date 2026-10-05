from import_export import fields

from ..models import Employee, Faculty, Specialization
from .base import ChapterForeignKeyWidget, ChapterManyToManyWidget, ChapterResource


class EmployeeResource(ChapterResource):
    """Employees; their specialization by name, their excluded faculties as an `a; b` list."""

    specialization = fields.Field(
        attribute="specialization",
        column_name="specialization",
        widget=ChapterForeignKeyWidget(Specialization),
    )

    excluded_faculties = fields.Field(
        attribute="excluded_faculties",
        column_name="excluded_faculties",
        widget=ChapterManyToManyWidget(Faculty),
    )

    class Meta:
        model = Employee
        fields = ("name", "specialization", "is_active", "excluded_faculties", "notes")
        export_order = fields
        import_id_fields = ("name",)
        clean_model_instances = True
        skip_unchanged = True
