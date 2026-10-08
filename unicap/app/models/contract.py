from collections.abc import Mapping

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from unicap import domain

from ..choices import ContractTypeChoices, DegreeChoices, EmploymentTypeChoices
from ..managers import ContractManager
from .abstracts import NotedModel


class Contract(NotedModel):
    """An employee's terms in their chapter, signed to a faculty or unsigned (no faculty).

    `position` is the signing order inside the chapter: when a group overflows, the
    contracts signed last are the ones not counted.

    `is_locked`: once signed, the contract stays in its faculty (the domain's rule).
    """

    chapter = models.ForeignKey(
        "app.Chapter",
        on_delete=models.CASCADE,
        related_name="contracts",
        verbose_name=_("chapter"),
    )
    employee = models.OneToOneField(
        "app.Employee",
        on_delete=models.RESTRICT,  # unless deleted with its chapter
        related_name="contract",
        verbose_name=_("employee"),
    )
    faculty = models.ForeignKey(
        "app.Faculty",
        on_delete=models.RESTRICT,  # unless deleted with its chapter
        related_name="contracts",
        verbose_name=_("faculty"),
        null=True,
        blank=True,
    )
    contract_type = models.CharField(
        verbose_name=_("contract type"),
        max_length=16,
        choices=ContractTypeChoices.choices,
        default=ContractTypeChoices.FULLTIME,
    )
    employment_type = models.CharField(
        verbose_name=_("employment type"),
        max_length=16,
        choices=EmploymentTypeChoices.choices,
        default=EmploymentTypeChoices.STAFF,
    )
    degree = models.CharField(
        verbose_name=_("degree"),
        max_length=16,
        choices=DegreeChoices.choices,
        default=DegreeChoices.PHD,
    )
    is_active = models.BooleanField(verbose_name=_("is active"), default=True)
    is_locked = models.BooleanField(
        verbose_name=_("locked to its faculty"),
        default=False,
        help_text=_("once signed, the contract cannot be moved to another faculty or unsigned"),
    )
    position = models.PositiveIntegerField(verbose_name=_("signing order"), default=0)

    objects: ContractManager = ContractManager()

    # set on page rows by `ContractManager.attach_statuses` (not stored)
    status: "domain.ContractStatus | None"
    is_counted: bool

    class Meta:
        verbose_name = _("contract")
        verbose_name_plural = _("contracts")
        ordering = ("position", "pk")
        constraints = (
            models.CheckConstraint(
                condition=~models.Q(contract_type="parttime", employment_type="staff"),
                name="hr_contract_parttime_is_borrowed",
                violation_error_message=_("a parttime contract is always borrowed."),
            ),
        )

    def __str__(self) -> str:
        return str(self.employee)

    # --- domain translation ---------------------------------------------------------

    def to_domain(
        self,
        *,
        employees: Mapping[int, domain.Employee] | None = None,
        faculties: Mapping[int, domain.Faculty] | None = None,
    ) -> domain.Contract:
        """Return the domain contract.

        Args:
            employees: already translated employees by row id.
            faculties: already translated faculties by row id (what they accept only).

        Raises:
            DomainError: a parttime staff contract.
        """
        employee = (employees or {}).get(self.employee_id) or self.employee.to_domain()

        faculty = None

        if self.faculty_id is not None:
            faculty = (faculties or {}).get(self.faculty_id)

            if faculty is None and self.faculty is not None:
                faculty = self.faculty.to_domain().faculty

        return domain.Contract(
            employee,
            domain.ContractType(self.contract_type),
            domain.EmploymentType(self.employment_type),
            faculty,
            degree=domain.Degree(self.degree),
            is_active=self.is_active,
            is_locked=self.is_locked,
        )

    @classmethod
    def from_domain(  # noqa: PLR0913 - the contract and the rows it points to
        cls,
        value: domain.Contract,
        *,
        chapter_id: int | None = None,
        employee_id: int | None = None,
        faculty_id: int | None = None,
        position: int = 0,
        instance: "Contract | None" = None,
    ) -> "Contract":
        """Copy a domain contract onto `instance` (or a new, unsaved row).

        Its employee and faculty are rows: give their ids (None faculty: unsigned).
        """
        contract = instance or cls()

        if chapter_id is not None:
            contract.chapter_id = chapter_id

        contract.employee_id = employee_id if employee_id is not None else value.employee.id
        contract.faculty_id = faculty_id
        contract.contract_type = value.contract_type.value
        contract.employment_type = value.employment_type.value
        contract.degree = value.degree.value
        contract.is_active = value.is_active
        contract.is_locked = value.is_locked
        contract.position = position
        return contract

    # --- urls -----------------------------------------------------------------------

    def get_absolute_url(self) -> str:
        return reverse("hr:contracts:details", kwargs={"pk": self.pk})

    def get_update_url(self) -> str:
        return reverse("hr:contracts:update", kwargs={"pk": self.pk})

    def get_delete_url(self) -> str:
        return reverse("hr:contracts:delete", kwargs={"pk": self.pk})

    def get_toggle_url(self) -> str:
        return reverse("hr:contracts:toggle", kwargs={"pk": self.pk})

    def get_toggle_lock_url(self) -> str:
        return reverse("hr:contracts:toggle-lock", kwargs={"pk": self.pk})
