from io import BytesIO
from pathlib import Path
from typing import IO

from ..querysets import ReportTemplateQuerySet
from ..reports import default_path
from .base import BaseManager


class ReportTemplateManager(BaseManager.from_queryset(ReportTemplateQuerySet)):  # type: ignore[misc]
    """Uploaded Word templates, falling back to the built-in ones."""

    def get_source(self, report: str, language: str) -> IO[bytes] | Path:
        """The template to fill: the one uploaded for `report` in `language`, else built-in.

        Example:
            ```python
            ReportTemplate.objects.get_source(ReportChoices.CAPACITY, "ar")
            ```
        """
        if template := self.for_report(report, language).first():
            with template.file.open("rb") as file:
                return BytesIO(file.read())

        return default_path(report, language)
