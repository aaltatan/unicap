from typing import Any

from import_export import fields

from ..choices import SpecializationTypeChoices
from ..models import Faculty, FacultySpecialization, Specialization
from .base import SAMPLE_ROWS, ChapterResource

SEPARATOR = ";"


class FacultyResource(ChapterResource):
    """Faculties with their numbers; accepted specializations as `a; b` lists by type.

    On import, listed specializations the faculty does not accept yet are added (at the
    end); nothing is removed, and existing shares keep their percentages.
    """

    specialized = fields.Field(column_name="specialized", readonly=False)
    supported = fields.Field(column_name="supported", readonly=False)

    labels = {
        "specialized": SpecializationTypeChoices.SPECIALIZED.label,
        "supported": SpecializationTypeChoices.SUPPORTED.label,
    }

    samples = {
        "students_per_phd": (25, 30),
        "current_students": (200, 300),
        "target_students": (250, 350),
    }

    class Meta:
        model = Faculty
        fields = (
            "name",
            "students_per_phd",
            "min_staff_percentage",
            "current_students",
            "target_students",
            "max_students",
            "min_specialized",
            "max_specialized",
            "min_supported",
            "max_supported",
            "max_share_rounding",
            "min_share_rounding",
            "staff_rounding",
            "masters_rounding",
            "specialized",
            "supported",
            "notes",
        )
        export_order = fields
        import_id_fields = ("name",)
        clean_model_instances = True

    def dehydrate_specialized(self, faculty: Faculty) -> str:
        return self._names(faculty, SpecializationTypeChoices.SPECIALIZED)

    def dehydrate_supported(self, faculty: Faculty) -> str:
        return self._names(faculty, SpecializationTypeChoices.SUPPORTED)

    def import_field(
        self,
        field: fields.Field,
        instance: Faculty,
        row: Any,
        is_m2m: bool = False,  # noqa: FBT001, FBT002 - import-export's signature
        **kwargs: Any,
    ) -> None:
        if field.column_name in ("specialized", "supported"):
            return  # saved with the shares, once the faculty exists

        super().import_field(field, instance, row, is_m2m, **kwargs)

    def after_save_instance(self, instance: Faculty, row: Any, **kwargs: Any) -> None:
        if kwargs.get("dry_run"):
            return

        accepted = {share.specialization.name: share for share in instance.shares.all()}

        position = len(accepted)

        for kind in (SpecializationTypeChoices.SPECIALIZED, SpecializationTypeChoices.SUPPORTED):
            for name in _split(row.get(kind.value)):
                if (share := accepted.get(name)) is not None:
                    if share.specialization_type != kind:
                        share.specialization_type = kind
                        share.save(update_fields=("specialization_type",))
                    continue

                specialization = Specialization.objects.filter(
                    chapter=self.chapter, name=name
                ).first()

                if specialization is None:
                    msg = f"{instance.name}: no specialization named {name!r} in this chapter"
                    raise ValueError(msg)

                accepted[name] = FacultySpecialization.objects.create(
                    faculty=instance,
                    specialization=specialization,
                    specialization_type=kind,
                    position=position,
                )

                position += 1

    def sample_value(self, column: str, index: int, options: dict[str, list[str]]) -> Any:
        """Lists of the chapter's specializations: each sample cell a different one."""
        if column not in ("specialized", "supported"):
            return super().sample_value(column, index, options)

        names = list(
            Specialization.objects.filter(chapter=self.chapter)
            .order_by("name")
            .values_list("name", flat=True)[: SAMPLE_ROWS * 2]
        )

        offset = index * 2 + (column == "supported")

        return names[offset] if offset < len(names) else ""

    def _names(self, faculty: Faculty, kind: str) -> str:
        return f"{SEPARATOR} ".join(
            share.specialization.name
            for share in faculty.shares.all()
            if share.specialization_type == kind
        )


def _split(value: object) -> list[str]:
    if not value:
        return []

    return [name.strip() for name in str(value).split(SEPARATOR) if name.strip()]
