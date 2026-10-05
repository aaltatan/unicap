from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from unicap import domain

from ..managers import ChapterManager
from .abstracts import NotedModel


class Chapter(NotedModel):
    """One chapter (a term / scenario) owning all of its data.

    Specializations, faculties (with their numbers and shares), employees and contracts all
    belong to one chapter; chapters never share rows, so a duplicate is a full copy.
    `is_default`: the chapter the app opens with.
    """

    name = models.CharField(verbose_name=_("name"), max_length=255, unique=True)
    max_students = models.PositiveIntegerField(
        verbose_name=_("max students"),
        null=True,
        blank=True,
        help_text=_("caps the chapter's capacity; empty: no cap"),
    )
    is_default = models.BooleanField(verbose_name=_("is default"), default=False)
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True)

    objects: ChapterManager = ChapterManager()

    class Meta:
        verbose_name = _("chapter")
        verbose_name_plural = _("chapters")
        ordering = ("-is_default", "name")
        constraints = (
            models.UniqueConstraint(
                fields=("is_default",),
                condition=models.Q(is_default=True),
                name="chapters_one_default_chapter",
            ),
        )

    def __str__(self) -> str:
        return self.name

    # --- domain translation ---------------------------------------------------------

    def to_domain(self) -> domain.Chapter:
        """Return the whole chapter as the domain's aggregate (validated on creation).

        Reads every owned row: prefetch with `Chapter.objects.with_domain_relations()`.
        Contracts keep their signing order (`position`).

        Raises:
            DomainError: when the rows break a domain rule.
        """
        specializations = {s.pk: s.to_domain() for s in self.specializations.all()}

        faculties = {
            f.pk: f.to_domain(specializations=specializations) for f in self.faculties.all()
        }

        employees = {
            e.pk: e.to_domain(specializations=specializations) for e in self.employees.all()
        }

        by_faculty = {pk: item.faculty for pk, item in faculties.items()}

        contracts = sorted(self.contracts.all(), key=lambda c: (c.position, c.pk))

        return domain.Chapter(
            self.name,
            tuple(c.to_domain(employees=employees, faculties=by_faculty) for c in contracts),
            self.max_students,
            faculties=tuple(faculties.values()),
            specializations=tuple(specializations.values()),
            employees=tuple(employees.values()),
        )

    @classmethod
    def from_domain(
        cls,
        value: domain.Chapter,
        *,
        instance: "Chapter | None" = None,
    ) -> "Chapter":
        """Copy a domain chapter's own fields onto `instance` (or a new, unsaved chapter).

        Only the chapter's settings: its rows are saved by their own `from_domain`.
        """
        chapter = instance or cls()
        chapter.name = value.name
        chapter.max_students = value.max_students
        return chapter

    # --- urls -----------------------------------------------------------------------

    def get_absolute_url(self) -> str:
        return reverse("chapters:details", kwargs={"pk": self.pk})

    def get_update_url(self) -> str:
        return reverse("chapters:update", kwargs={"pk": self.pk})

    def get_delete_url(self) -> str:
        return reverse("chapters:delete", kwargs={"pk": self.pk})
