from collections.abc import Mapping

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from unicap import domain

from ..choices import ContractTypeChoices, SpecializationTypeChoices
from ..managers import FacultySpecializationManager

DEFAULT_MASTERS_PER_PHD = 2

PERCENTAGE_VALIDATORS = [MinValueValidator(0), MaxValueValidator(100)]


class FacultySpecialization(models.Model):
    """A specialization a faculty accepts (specialized or supported), and its share.

    Leave `percentage` empty for the new method (only specialized / supported matters).
    `position` orders the faculty's specializations (drag and drop in the form).
    """

    faculty = models.ForeignKey(
        "app.Faculty",
        on_delete=models.CASCADE,
        related_name="shares",
        verbose_name=_("faculty"),
    )
    specialization = models.ForeignKey(
        "app.Specialization",
        on_delete=models.RESTRICT,  # unless deleted with its chapter
        related_name="shares",
        verbose_name=_("specialization"),
    )
    specialization_type = models.CharField(
        verbose_name=_("type"),
        max_length=16,
        choices=SpecializationTypeChoices.choices,
        default=SpecializationTypeChoices.SPECIALIZED,
    )
    percentage = models.FloatField(
        verbose_name=_("percentage"),
        null=True,
        blank=True,
        validators=PERCENTAGE_VALIDATORS,
    )
    min_percentage = models.FloatField(
        verbose_name=_("min percentage"),
        null=True,
        blank=True,
        validators=PERCENTAGE_VALIDATORS,
    )
    max_percentage = models.FloatField(
        verbose_name=_("max percentage"),
        null=True,
        blank=True,
        validators=PERCENTAGE_VALIDATORS,
    )
    min_teachers = models.PositiveIntegerField(
        verbose_name=_("min teachers"),
        null=True,
        blank=True,
    )
    max_teachers = models.PositiveIntegerField(
        verbose_name=_("max teachers"),
        null=True,
        blank=True,
    )
    contract_type = models.CharField(
        verbose_name=_("contract type"),
        max_length=16,
        choices=ContractTypeChoices.choices,
        blank=True,
        default="",
        help_text=_("only this contract type counts for the specialization here; empty: any"),
    )
    calculate_masters = models.BooleanField(
        verbose_name=_("calculate masters"),
        default=True,
        help_text=_("off: the specialization's masters are left out of this faculty"),
    )
    masters_per_phd = models.PositiveSmallIntegerField(
        verbose_name=_("masters per PhD"),
        default=DEFAULT_MASTERS_PER_PHD,
        validators=[MinValueValidator(1)],
        help_text=_("how many of its masters are worth one PhD"),
    )
    position = models.PositiveIntegerField(verbose_name=_("position"), default=0)

    objects: FacultySpecializationManager = FacultySpecializationManager()

    class Meta:
        verbose_name = _("accepted specialization")
        verbose_name_plural = _("accepted specializations")
        ordering = ("position", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("faculty", "specialization"),
                name="edu_faculty_specialization_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(masters_per_phd__gt=0),
                name="edu_share_masters_per_phd_positive",
                violation_error_message=_("masters per PhD must be positive."),
            ),
        )

    def __str__(self) -> str:
        return f"{self.faculty} · {self.specialization}"

    # --- domain translation ---------------------------------------------------------

    def to_domain(
        self,
        *,
        specializations: Mapping[int, domain.Specialization] | None = None,
    ) -> domain.Share:
        """Return the share; whether it is specialized or supported is the faculty's.

        Args:
            specializations: already translated specializations by row id.
        """
        specialization = (specializations or {}).get(self.specialization_id)

        return domain.Share(
            specialization or self.specialization.to_domain(),
            percentage=self.percentage,
            min_percentage=self.min_percentage,
            max_percentage=self.max_percentage,
            min_teachers=self.min_teachers,
            max_teachers=self.max_teachers,
            contract_type=domain.ContractType(self.contract_type) if self.contract_type else None,
            calculate_masters=self.calculate_masters,
            masters_per_phd=self.masters_per_phd,
        )

    @classmethod
    def from_domain(  # noqa: PLR0913 - the share, where it goes, its type and order
        cls,
        value: domain.Share,
        *,
        faculty_id: int | None = None,
        specialization_id: int | None = None,
        specialization_type: domain.SpecializationType = domain.SpecializationType.SPECIALIZED,
        position: int = 0,
        instance: "FacultySpecialization | None" = None,
    ) -> "FacultySpecialization":
        """Copy a domain share onto `instance` (or a new, unsaved row)."""
        share = instance or cls()

        if faculty_id is not None:
            share.faculty_id = faculty_id

        if specialization_id is not None:
            share.specialization_id = specialization_id

        share.specialization_type = specialization_type.value
        share.percentage = value.percentage
        share.min_percentage = value.min_percentage
        share.max_percentage = value.max_percentage
        share.min_teachers = value.min_teachers
        share.max_teachers = value.max_teachers
        share.contract_type = value.contract_type.value if value.contract_type else ""
        share.calculate_masters = value.calculate_masters
        share.masters_per_phd = value.masters_per_phd
        share.position = position
        return share
