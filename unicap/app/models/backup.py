from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ..choices import BackupScopeChoices, BackupSectionChoices
from ..managers import BackupManager
from ..storages import PrivateStorage
from .abstracts import NotedModel


class Backup(NotedModel):
    """A saved copy of the data (a JSON file): the whole system, a chapter or a section.

    `chapter` is the chapter it was taken from (kept by name when that chapter is gone).
    """

    scope = models.CharField(
        verbose_name=_("scope"),
        max_length=16,
        choices=BackupScopeChoices.choices,
    )
    section = models.CharField(
        verbose_name=_("section"),
        max_length=32,
        choices=BackupSectionChoices.choices,
        blank=True,
        default="",
    )
    chapter = models.ForeignKey(
        "app.Chapter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backups",
        verbose_name=_("chapter"),
    )
    chapter_name = models.CharField(verbose_name=_("chapter"), max_length=255, blank=True)
    file = models.FileField(
        verbose_name=_("file"),
        upload_to="backups/",
        storage=PrivateStorage(),  # downloaded through `backups:download` only
    )
    size = models.PositiveIntegerField(verbose_name=_("size"), default=0)
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("created by"),
    )

    objects: BackupManager = BackupManager()

    class Meta:
        verbose_name = _("backup")
        verbose_name_plural = _("backups")
        ordering = ("-created_at", "-pk")
        permissions = (("restore_backup", _("Can restore a backup")),)

    def __str__(self) -> str:
        what = self.get_section_display() if self.section else self.get_scope_display()
        where = f" · {self.chapter_name}" if self.chapter_name else ""
        return f"{what}{where} · {self.created_at:%Y-%m-%d %H:%M}"

    # --- urls -----------------------------------------------------------------------

    def get_download_url(self) -> str:
        return reverse("backups:download", kwargs={"pk": self.pk})

    def get_restore_url(self) -> str:
        return reverse("backups:restore", kwargs={"pk": self.pk})

    def get_delete_url(self) -> str:
        return reverse("backups:delete", kwargs={"pk": self.pk})
