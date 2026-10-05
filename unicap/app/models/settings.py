from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel

from ..choices import PER_PAGE_CHOICES, ModalSizeChoices
from ..managers import SectionSettingsManager

PER_PAGE = [(value, str(value)) for value in PER_PAGE_CHOICES]

MAX_OPTIMIZER_ROUNDS = 200


class AppSettings(SingletonModel):
    """The app's settings (one row, edited in the admin panel): the defaults of every page."""

    project_name = models.CharField(
        verbose_name=_("project name"), max_length=100, default="UniCap"
    )
    per_page = models.PositiveSmallIntegerField(
        verbose_name=_("rows per page"),
        choices=PER_PAGE,
        default=25,
    )
    modal_size = models.CharField(
        verbose_name=_("modal size"),
        max_length=8,
        choices=ModalSizeChoices.choices,
        default=ModalSizeChoices.LARGE,
    )
    resizable_modals = models.BooleanField(
        verbose_name=_("resizable modals"),
        default=True,
        help_text=_("drag a modal's corner to resize it, or maximize it"),
    )
    remember_table_state = models.BooleanField(
        verbose_name=_("remember table state"),
        default=True,
        help_text=_(
            "a table opens again with the filters, search, sorting and page it was left with"
        ),
    )
    optimizer_rounds = models.PositiveSmallIntegerField(
        verbose_name=_("optimizer rounds"),
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_OPTIMIZER_ROUNDS)],
        help_text=_(
            "how many times the optimizer goes over every contract looking for a better "
            "place: more can find better placements, but takes longer"
        ),
    )

    class Meta:
        verbose_name = _("app settings")

    def __str__(self) -> str:
        return str(self._meta.verbose_name)


class SectionSettings(SingletonModel):
    """One section's settings (one row each); empty: the app's default."""

    per_page = models.PositiveSmallIntegerField(
        verbose_name=_("rows per page"),
        choices=PER_PAGE,
        null=True,
        blank=True,
        help_text=_("empty: the app's default"),
    )
    form_modal_size = models.CharField(
        verbose_name=_("form modal size"),
        max_length=8,
        choices=ModalSizeChoices.choices,
        blank=True,
        default="",
        help_text=_("empty: the app's default"),
    )
    details_modal_size = models.CharField(
        verbose_name=_("details modal size"),
        max_length=8,
        choices=ModalSizeChoices.choices,
        blank=True,
        default="",
        help_text=_("empty: the app's default"),
    )

    objects: SectionSettingsManager = SectionSettingsManager()

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return str(self._meta.verbose_name)


class ChapterSettings(SectionSettings):
    """The chapters' page."""

    class Meta:
        verbose_name = _("chapters settings")


class SpecializationSettings(SectionSettings):
    """The specializations' page."""

    class Meta:
        verbose_name = _("specializations settings")


class FacultySettings(SectionSettings):
    """Faculties: their form and details hold tables, so they open extra large."""

    form_modal_size = models.CharField(
        verbose_name=_("form modal size"),
        max_length=8,
        choices=ModalSizeChoices.choices,
        blank=True,
        default=ModalSizeChoices.EXTRA_LARGE,
        help_text=_("empty: the app's default"),
    )
    details_modal_size = models.CharField(
        verbose_name=_("details modal size"),
        max_length=8,
        choices=ModalSizeChoices.choices,
        blank=True,
        default=ModalSizeChoices.EXTRA_LARGE,
        help_text=_("empty: the app's default"),
    )

    class Meta:
        verbose_name = _("faculties settings")


class EmployeeSettings(SectionSettings):
    """The employees' page."""

    class Meta:
        verbose_name = _("employees settings")


class ContractSettings(SectionSettings):
    """The contracts' page."""

    class Meta:
        verbose_name = _("contracts settings")
