from collections.abc import Mapping

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from unicap import domain

from ..managers import EmployeeManager
from .abstracts import NotedModel


class Employee(NotedModel):
    """A teacher of one chapter. Inactive: their contract leaves the calculation.

    `excluded_faculties` (optional): the chapter's faculties they cannot be counted in.
    """

    chapter = models.ForeignKey(
        "app.Chapter",
        on_delete=models.CASCADE,
        related_name="employees",
        verbose_name=_("chapter"),
    )
    name = models.CharField(verbose_name=_("name"), max_length=255)
    specialization = models.ForeignKey(
        "app.Specialization",
        on_delete=models.RESTRICT,  # unless deleted with its chapter
        related_name="employees",
        verbose_name=_("specialization"),
    )
    is_active = models.BooleanField(verbose_name=_("is active"), default=True)
    excluded_faculties = models.ManyToManyField(
        "app.Faculty",
        related_name="excluded_employees",
        verbose_name=_("cannot be counted in"),
        blank=True,
        help_text=_("signed to one of these faculties, the contract is never counted there"),
    )

    objects: EmployeeManager = EmployeeManager()

    # set on page rows by `EmployeeManager.attach_statuses` (not stored)
    status: "domain.ContractStatus | None"

    class Meta:
        verbose_name = _("employee")
        verbose_name_plural = _("employees")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    # --- domain translation ---------------------------------------------------------

    def to_domain(
        self,
        *,
        specializations: Mapping[int, domain.Specialization] | None = None,
    ) -> domain.Employee:
        """Return the domain employee (its id is the row's).

        Reads `excluded_faculties`: prefetch them when translating many rows.

        Args:
            specializations: already translated specializations by row id.
        """
        specialization = (specializations or {}).get(self.specialization_id)

        return domain.Employee(
            self.pk,
            self.name,
            specialization or self.specialization.to_domain(),
            is_active=self.is_active,
            excluded_faculties=frozenset(f.name for f in self.excluded_faculties.all()),
        )

    @classmethod
    def from_domain(
        cls,
        value: domain.Employee,
        *,
        chapter_id: int | None = None,
        specialization_id: int | None = None,
        instance: "Employee | None" = None,
    ) -> "Employee":
        """Copy a domain employee onto `instance` (or a new, unsaved row).

        The specialization is a row: give its id (domain values hold it by name). The
        excluded faculties are rows too, set once the employee is saved
        (`ChapterManager.create_from_domain`).
        """
        employee = instance or cls()

        if chapter_id is not None:
            employee.chapter_id = chapter_id

        employee.name = value.name
        employee.is_active = value.is_active

        if specialization_id is not None:
            employee.specialization_id = specialization_id

        return employee

    # --- urls -----------------------------------------------------------------------

    def get_absolute_url(self) -> str:
        return reverse("hr:employees:details", kwargs={"pk": self.pk})

    def get_update_url(self) -> str:
        return reverse("hr:employees:update", kwargs={"pk": self.pk})

    def get_delete_url(self) -> str:
        return reverse("hr:employees:delete", kwargs={"pk": self.pk})

    def get_toggle_url(self) -> str:
        return reverse("hr:employees:toggle", kwargs={"pk": self.pk})
