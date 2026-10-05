from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from django.apps import apps
from django.db import models

if TYPE_CHECKING:
    from ..models import SectionSettings


@dataclass(frozen=True)
class ViewSettings:
    """What a section's pages use: its own settings, else the app's."""

    per_page: int
    form_modal_size: str
    details_modal_size: str


class SectionSettingsManager(models.Manager):
    """A section's settings (a singleton), resolved against the app's defaults."""

    def effective(self) -> ViewSettings:
        """The section's settings, an empty one taking the app's default.

        Example:
            ```python
            FacultySettings.objects.effective().details_modal_size  # "xl"
            ```
        """
        section = cast("type[SectionSettings]", self.model).get_solo()
        app = apps.get_model("app", "AppSettings").get_solo()

        return ViewSettings(
            per_page=section.per_page or app.per_page,
            form_modal_size=section.form_modal_size or app.modal_size,
            details_modal_size=section.details_modal_size or app.modal_size,
        )
