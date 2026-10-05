from typing_extensions import Self

from .base import BaseQuerySet


class ReportTemplateQuerySet(BaseQuerySet):
    """Uploaded Word templates."""

    search_fields = ("report", "notes")

    def for_report(self, report: str, language: str) -> Self:
        """The template uploaded for `report` in `language` (at most one)."""
        return self.filter(report=report, language=language)
