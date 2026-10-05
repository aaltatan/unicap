from collections.abc import Mapping

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from unicap import domain

from ..choices import RoundingChoices, SpecializationTypeChoices
from ..managers import FacultyManager
from .abstracts import NotedModel


class Faculty(NotedModel):
    """A faculty of one chapter, with the numbers it works with there.

    What it accepts (specialized / supported specializations, each with its share) are
    its `shares`. A faculty with contracts cannot be deleted (unsign them first).
    """

    chapter = models.ForeignKey(
        "app.Chapter",
        on_delete=models.CASCADE,
        related_name="faculties",
        verbose_name=_("chapter"),
    )
    name = models.CharField(verbose_name=_("name"), max_length=255)
    students_per_phd = models.PositiveIntegerField(
        verbose_name=_("students per PhD"),
        validators=[MinValueValidator(1)],
    )
    min_staff_percentage = models.FloatField(
        verbose_name=_("min staff percentage"),
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    current_students = models.PositiveIntegerField(
        verbose_name=_("current students"),
        null=True,
        blank=True,
    )
    target_students = models.PositiveIntegerField(
        verbose_name=_("target students"),
        null=True,
        blank=True,
    )
    max_students = models.PositiveIntegerField(
        verbose_name=_("max students"),
        null=True,
        blank=True,
    )
    min_specialized = models.PositiveIntegerField(
        verbose_name=_("min specialized PhDs"),
        null=True,
        blank=True,
    )
    max_specialized = models.PositiveIntegerField(
        verbose_name=_("max specialized PhDs"),
        null=True,
        blank=True,
    )
    min_supported = models.PositiveIntegerField(
        verbose_name=_("min supported PhDs"),
        null=True,
        blank=True,
    )
    max_supported = models.PositiveIntegerField(
        verbose_name=_("max supported PhDs"),
        null=True,
        blank=True,
    )
    max_share_rounding = models.CharField(
        verbose_name=_("max share rounding"),
        max_length=16,
        choices=RoundingChoices.choices,
        default=RoundingChoices.FLOOR,
        help_text=_("a specialization's max percentage in whole teachers: the most it may count"),
    )
    min_share_rounding = models.CharField(
        verbose_name=_("min share rounding"),
        max_length=16,
        choices=RoundingChoices.choices,
        default=RoundingChoices.CEILING,
        help_text=_("a specialization's min percentage in whole teachers: the fewest it needs"),
    )
    masters_rounding = models.CharField(
        verbose_name=_("masters rounding"),
        max_length=16,
        choices=RoundingChoices.choices,
        default=RoundingChoices.FLOOR,
        help_text=_("the faculty's masters in whole PhDs (e.g. one master alone)"),
    )
    staff_rounding = models.CharField(
        verbose_name=_("min staff rounding"),
        max_length=16,
        choices=RoundingChoices.choices,
        default=RoundingChoices.CEILING,
        help_text=_("the min staff percentage in whole fulltime staff: the fewest it needs"),
    )

    objects: FacultyManager = FacultyManager()

    # set on rows by `FacultyManager.attach_reports` (not stored)
    report: "domain.FacultyReport | None"

    class Meta:
        verbose_name = _("faculty")
        verbose_name_plural = _("faculties")
        ordering = ("name",)
        constraints = (
            models.UniqueConstraint(
                fields=("chapter", "name"),
                name="edu_faculty_unique_name_per_chapter",
            ),
            models.CheckConstraint(
                condition=models.Q(students_per_phd__gt=0),
                name="edu_faculty_students_per_phd_positive",
                violation_error_message=_("students per PhD must be positive."),
            ),
        )

    def __str__(self) -> str:
        return self.name

    # --- domain translation ---------------------------------------------------------

    def to_domain(
        self,
        *,
        specializations: Mapping[int, domain.Specialization] | None = None,
    ) -> domain.ChapterFaculty:
        """Return the faculty with its numbers and shares (a `ChapterFaculty`).

        Args:
            specializations: already translated specializations by row id, so a chapter
                translates each one once; missing ones are translated here.

        Raises:
            DomainError: the numbers or shares break a domain rule.
        """
        rows = sorted(self.shares.all(), key=lambda share: (share.position, share.pk))

        shares = [(row, row.to_domain(specializations=specializations)) for row in rows]

        def of_type(kind: str) -> tuple[domain.Specialization, ...]:
            return tuple(
                value.specialization for row, value in shares if row.specialization_type == kind
            )

        faculty = domain.Faculty(
            self.name,
            specialized=of_type(SpecializationTypeChoices.SPECIALIZED),
            supported=of_type(SpecializationTypeChoices.SUPPORTED),
        )

        return domain.ChapterFaculty(
            faculty,
            students_per_phd=self.students_per_phd,
            min_staff_percentage=self.min_staff_percentage,
            current_students=self.current_students,
            target_students=self.target_students,
            max_students=self.max_students,
            shares=tuple(value for _, value in shares),
            min_specialized=self.min_specialized,
            max_specialized=self.max_specialized,
            min_supported=self.min_supported,
            max_supported=self.max_supported,
            max_share_rounding=domain.RoundingMode(self.max_share_rounding),
            min_share_rounding=domain.RoundingMode(self.min_share_rounding),
            staff_rounding=domain.RoundingMode(self.staff_rounding),
            masters_rounding=domain.RoundingMode(self.masters_rounding),
        )

    @classmethod
    def from_domain(
        cls,
        value: domain.ChapterFaculty,
        *,
        chapter_id: int | None = None,
        instance: "Faculty | None" = None,
    ) -> "Faculty":
        """Copy a faculty's name and numbers onto `instance` (or a new, unsaved row).

        Its shares are rows of their own: `FacultySpecialization.from_domain`.
        """
        faculty = instance or cls()

        if chapter_id is not None:
            faculty.chapter_id = chapter_id

        faculty.name = value.name
        faculty.students_per_phd = value.students_per_phd
        faculty.min_staff_percentage = value.min_staff_percentage
        faculty.current_students = value.current_students
        faculty.target_students = value.target_students
        faculty.max_students = value.max_students
        faculty.min_specialized = value.min_specialized
        faculty.max_specialized = value.max_specialized
        faculty.min_supported = value.min_supported
        faculty.max_supported = value.max_supported
        faculty.max_share_rounding = value.max_share_rounding.value
        faculty.min_share_rounding = value.min_share_rounding.value
        faculty.staff_rounding = value.staff_rounding.value
        faculty.masters_rounding = value.masters_rounding.value
        return faculty

    # --- urls -----------------------------------------------------------------------

    def get_absolute_url(self) -> str:
        return reverse("edu:faculties:details", kwargs={"pk": self.pk})

    def get_update_url(self) -> str:
        return reverse("edu:faculties:update", kwargs={"pk": self.pk})

    def get_delete_url(self) -> str:
        return reverse("edu:faculties:delete", kwargs={"pk": self.pk})
