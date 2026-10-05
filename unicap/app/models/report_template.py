from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..choices import ReportChoices
from ..managers import ReportTemplateManager
from ..validators import validate_docx_template
from .abstracts import NotedModel


class ReportTemplate(NotedModel):
    """The Word (.docx) template of one report in one language, edited by admins.

    Without one, the report uses its built-in template (`reports/defaults/`). Values are
    docxtpl tags: `{{ chapter.name }}`, `{%tr for f in faculties %}` (`reports.VARIABLES`).
    """

    report = models.CharField(
        verbose_name=_("report"),
        max_length=32,
        choices=ReportChoices.choices,
    )
    language = models.CharField(
        verbose_name=_("language"),
        max_length=8,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    file = models.FileField(
        verbose_name=_("file"),
        upload_to="report-templates/",
        validators=[FileExtensionValidator(["docx"]), validate_docx_template],
        help_text=_("a Word (.docx) file holding docxtpl tags such as {{ chapter.name }}"),
    )
    updated_at = models.DateTimeField(verbose_name=_("updated at"), auto_now=True)

    objects: ReportTemplateManager = ReportTemplateManager()

    class Meta:
        verbose_name = _("report template")
        verbose_name_plural = _("report templates")
        ordering = ("report", "language")
        constraints = (
            models.UniqueConstraint(
                fields=("report", "language"),
                name="app_report_template_unique_report_language",
            ),
        )

    def __str__(self) -> str:
        return f"{self.get_report_display()} ({self.get_language_display()})"
