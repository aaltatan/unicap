from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from unicap import domain

from ..managers import SpecializationManager
from .abstracts import NotedModel


class Specialization(NotedModel):
    """A specialization of one chapter. Inactive: all of its contracts leave the calculation."""

    chapter = models.ForeignKey(
        "app.Chapter",
        on_delete=models.CASCADE,
        related_name="specializations",
        verbose_name=_("chapter"),
    )
    name = models.CharField(verbose_name=_("name"), max_length=255)
    is_active = models.BooleanField(verbose_name=_("is active"), default=True)

    objects: SpecializationManager = SpecializationManager()

    class Meta:
        verbose_name = _("specialization")
        verbose_name_plural = _("specializations")
        ordering = ("name",)
        constraints = (
            models.UniqueConstraint(
                fields=("chapter", "name"),
                name="edu_specialization_unique_name_per_chapter",
            ),
        )

    def __str__(self) -> str:
        return self.name

    # --- domain translation ---------------------------------------------------------

    def to_domain(self) -> domain.Specialization:
        return domain.Specialization(self.name, is_active=self.is_active)

    @classmethod
    def from_domain(
        cls,
        value: domain.Specialization,
        *,
        chapter_id: int | None = None,
        instance: "Specialization | None" = None,
    ) -> "Specialization":
        """Copy a domain specialization onto `instance` (or a new, unsaved row of `chapter_id`)."""
        specialization = instance or cls()

        if chapter_id is not None:
            specialization.chapter_id = chapter_id

        specialization.name = value.name
        specialization.is_active = value.is_active
        return specialization

    # --- urls -----------------------------------------------------------------------

    def get_absolute_url(self) -> str:
        return reverse("edu:specializations:details", kwargs={"pk": self.pk})

    def get_update_url(self) -> str:
        return reverse("edu:specializations:update", kwargs={"pk": self.pk})

    def get_delete_url(self) -> str:
        return reverse("edu:specializations:delete", kwargs={"pk": self.pk})

    def get_toggle_url(self) -> str:
        return reverse("edu:specializations:toggle", kwargs={"pk": self.pk})
