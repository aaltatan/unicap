from typing import Any

from django.db.models import Max
from import_export import fields

from ..models import Contract, Employee, Faculty
from .base import ChapterForeignKeyWidget, ChapterResource


class ContractResource(ChapterResource):
    """Contracts; the employee and faculty by name (no faculty: unsigned).

    A new contract, or one whose faculty changes, is signed last; a locked one cannot change
    its faculty (unless the row unlocks it).
    """

    employee = fields.Field(
        attribute="employee",
        column_name="employee",
        widget=ChapterForeignKeyWidget(Employee),
    )
    faculty = fields.Field(
        attribute="faculty",
        column_name="faculty",
        widget=ChapterForeignKeyWidget(Faculty),
    )

    class Meta:
        model = Contract
        fields = (
            "employee",
            "faculty",
            "degree",
            "contract_type",
            "employment_type",
            "is_active",
            "is_locked",
            "notes",
        )
        export_order = fields
        import_id_fields = ("employee",)
        clean_model_instances = True
        skip_unchanged = True

    def before_save_instance(self, instance: Contract, row: Any, **kwargs: Any) -> None:
        stored = Contract.objects.filter(pk=instance.pk)

        previous = stored.values_list("faculty_id", flat=True).first()

        if instance.is_locked:
            Contract.objects.check_movable(stored, instance.faculty_id)

        if instance.pk is None or previous != instance.faculty_id:
            last = Contract.objects.filter(chapter=self.chapter).aggregate(last=Max("position"))
            instance.position = (last["last"] or 0) + 1
