from typing import Self

from .base import BaseQuerySet


class BackupQuerySet(BaseQuerySet):
    """Saved backups."""

    search_fields = ("chapter_name", "notes")

    def for_listing(
        self, *, scope: str = "", section: str = "", chapter_id: int | None = None
    ) -> Self:
        """The backups to show, narrowed by scope, section and chapter when given."""
        rows = self.select_related("created_by")

        if scope:
            rows = rows.filter(scope=scope)

        if section:
            rows = rows.filter(section=section)

        if chapter_id is not None:
            rows = rows.filter(chapter_id=chapter_id)

        return rows
