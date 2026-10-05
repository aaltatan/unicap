from ..models import Specialization
from .base import ChapterResource


class SpecializationResource(ChapterResource):
    class Meta:
        model = Specialization
        fields = ("name", "is_active", "notes")
        export_order = fields
        import_id_fields = ("name",)
        clean_model_instances = True
        skip_unchanged = True
