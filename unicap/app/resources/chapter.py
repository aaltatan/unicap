from typing import Any

from django.db.models import Model

from ..models import Chapter
from .base import TranslatedResource


class ChapterResource(TranslatedResource):
    """Chapters' settings (their rows are exported from their own tables)."""

    def __init__(self, *, chapter: Model | None = None, **kwargs: Any) -> None:
        """Take `chapter` like every resource (chapters are not in one)."""
        super().__init__(**kwargs)

    class Meta:
        model = Chapter
        fields = (
            "name",
            "max_students",
            "is_default",
            "notes",
        )
        export_order = fields
        import_id_fields = ("name",)
