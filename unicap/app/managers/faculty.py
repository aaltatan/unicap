from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django.apps import apps

from ..querysets import FacultyQuerySet
from .base import ChapterOwnedManager, chapters

if TYPE_CHECKING:
    from django.forms import BaseInlineFormSet

    from ..models import Faculty


class FacultyManager(ChapterOwnedManager.from_queryset(FacultyQuerySet)):  # type: ignore[misc]
    """Faculties: saved with their accepted specializations, in one validated transaction.

    A faculty with contracts cannot be deleted (unsign or move them first).
    """

    def clear_shares(self, chapter_id: int, ids: Iterable[int]) -> int:
        """Remove every accepted specialization of these faculties (they accept none).

        Raises:
            DomainError: the chapter would break a domain rule; nothing is saved.
        """
        with chapters().validated(chapter_id):
            faculties = self.filter(chapter_id=chapter_id, pk__in=list(ids))
            count = faculties.count()
            apps.get_model("app", "FacultySpecialization").objects.filter(
                faculty__in=faculties,
            ).delete()

        return count

    def save_with_shares(
        self, faculty: "Faculty", shares: "BaseInlineFormSet[Any, Any, Any]"
    ) -> "Faculty":
        """Save the faculty and its accepted specializations, in the formset's order.

        Raises:
            DomainError: a share or the chapter would break a domain rule; nothing is saved.
        """

        def save_shares(saved: "Faculty") -> None:
            shares.instance = saved

            shares.save(commit=False)  # sorts the forms into new / changed / deleted

            for row in shares.deleted_objects:
                row.delete()

            deleted = set(shares.deleted_forms)

            kept = [
                form
                for form in shares.forms
                if form not in deleted and (form.instance.pk or form.has_changed())
            ]

            ordered = sorted(kept, key=lambda form: form.cleaned_data.get("position") or 0)

            for position, form in enumerate(ordered):
                form.instance.faculty = saved
                form.instance.position = position
                form.instance.save()

            saved.to_domain()  # the faculty with its shares, before the chapter's check

        new_rows = [form.instance for form in shares.forms if form.instance.pk is None]

        try:
            return self.save_validated(faculty, after=save_shares)
        except Exception:
            for row in new_rows:  # rolled back: the rows must look unsaved again
                row.pk = None
                row._state.adding = True  # noqa: SLF001
            raise

    def attach_reports(self, faculties: Iterable["Faculty"], chapter_id: int) -> list["Faculty"]:
        """Set `report` (the domain's `FacultyReport`) on each faculty row.

        The whole chapter is evaluated once; a faculty's report holds its capacity, staff
        percentage, head counts, violations and the status of every contract signed to it.
        """
        snapshot = chapters().get_snapshot(chapter_id)

        report = snapshot.report()

        rows = list(faculties)

        for row in rows:
            faculty = snapshot.faculty_of(row.pk)
            row.report = report.report_of(faculty) if faculty else None

        return rows
