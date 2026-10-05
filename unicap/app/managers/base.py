"""Shared managers: the base, and the one every chapter-owned model's manager builds on."""

from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING, Any

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..exceptions import UserError

if TYPE_CHECKING:
    from import_export.resources import ModelResource
    from import_export.results import Result
    from tablib import Dataset

    from .chapter import ChapterManager


def check_rows(rows: Iterable[models.Model], values: Mapping[str, Any]) -> None:
    """Each row with `values` must keep its own constraints (a parttime contract is borrowed).

    Raises:
        UserError: the rows that would break one, with the reason (the first ten).
    """
    problems = []

    for row in rows:
        for name, value in values.items():
            setattr(row, name, value)

        try:
            row.validate_constraints()
        except ValidationError as error:
            problems.append(f"{row}: {' '.join(error.messages)}")

    if problems:
        raise UserError("\n".join(problems[:10]))


class BaseManager(models.Manager):
    """Base manager: every model's manager is `BaseManager.from_queryset(XQuerySet)`."""


class ChapterOwnedManager(BaseManager):
    """Writes to rows owned by one chapter: each commits only if the chapter stays valid.

    Every write runs in `Chapter.objects.validated(chapter_id)`: the whole chapter is
    rebuilt as a domain `Chapter` before commit, so a `DomainError` rolls it back.
    """

    def save_validated(
        self,
        instance: models.Model,
        *,
        after: Callable[[models.Model], object] | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> models.Model:
        """Save `instance`, then `after(instance)` (its nested rows), if the chapter stays valid.

        Raises:
            DomainError: the chapter would break a domain rule; nothing is saved.
        """
        with chapters().validated(getattr(instance, "chapter_id")):  # noqa: B009 - any owned row
            instance.save(update_fields=update_fields)

            if after is not None:
                after(instance)

        return instance

    def bulk_set(self, chapter_id: int, ids: Iterable[int], values: Mapping[str, Any]) -> int:
        """Set the same `values` on several rows of one chapter: all of them or none.

        Raises:
            DomainError: the chapter would break a domain rule; nothing is saved.

        Example:
            ```python
            Specialization.objects.bulk_set(chapter.pk, [1, 2], {"is_active": False})
            ```
        """
        with chapters().validated(chapter_id):
            rows = self.filter(chapter_id=chapter_id, pk__in=list(ids))
            check_rows(rows, values)
            return rows.update(**values)

    def delete_many(self, chapter_id: int, ids: Iterable[int]) -> int:
        """Delete several rows of one chapter in one transaction: all of them or none.

        Raises:
            UserError: a row is still used by another (a protected relation).
            DomainError: the chapter would break a domain rule.
        """
        with chapters().validated(chapter_id):
            try:
                deleted, _counts = self.filter(chapter_id=chapter_id, pk__in=list(ids)).delete()
            except (models.ProtectedError, models.RestrictedError) as error:
                msg = _("still in use by %(users)s: remove it from them first.") % {
                    "users": in_use_by(blocking_rows(error)),
                }
                raise UserError(msg) from error

        return deleted

    def import_rows(self, resource: "ModelResource", dataset: "Dataset") -> int:
        """Import a file's rows into the resource's chapter: all of them or none.

        Returns:
            How many rows were added or updated.

        Raises:
            UserError: a row is invalid (every problem, one per line).
            DomainError: the chapter would break a domain rule.
        """
        with chapters().validated(resource.chapter.pk):
            result = resource.import_data(dataset, dry_run=False, use_transactions=False)

            if problems := _import_problems(result):
                raise UserError("\n".join(problems))

        return result.totals.get("new", 0) + result.totals.get("update", 0)

    def toggle_active(self, instance: models.Model) -> models.Model:
        """Switch `is_active` on or off: off leaves its contracts out of the calculation."""
        setattr(instance, "is_active", not getattr(instance, "is_active"))  # noqa: B009, B010

        return self.save_validated(instance, update_fields=("is_active",))


def blocking_rows(error: models.ProtectedError | models.RestrictedError) -> set[models.Model]:
    """The rows that keep a delete from happening."""
    if isinstance(error, models.ProtectedError):
        return set(error.protected_objects)

    return set(error.restricted_objects)


def in_use_by(rows: Iterable[models.Model], *, limit: int = 5) -> str:
    """`contracts: Ali, Omar; accepted specializations: Dentistry · Biology` (first few)."""
    by_model: dict[str, set[str]] = {}

    for row in rows:
        by_model.setdefault(str(row._meta.verbose_name_plural), set()).add(str(row))  # noqa: SLF001

    return "; ".join(
        f"{label}: {', '.join(sorted(names)[:limit])}{'…' if len(names) > limit else ''}"
        for label, names in sorted(by_model.items())
    )


def chapters() -> "ChapterManager":
    """The chapters' manager, looked up lazily: chapter-owned apps never import it."""
    return apps.get_model("app", "Chapter").objects


def _import_problems(result: "Result") -> list[str]:
    """Every row error and invalid row of an import result, as `row N: message`."""
    problems = [
        f"row {number}: {error.error}" for number, errors in result.row_errors() for error in errors
    ]

    problems += [
        f"row {row.number}: {field}: {'; '.join(str(m) for m in messages)}"
        for row in result.invalid_rows
        for field, messages in row.error_dict.items()
    ]

    return problems
