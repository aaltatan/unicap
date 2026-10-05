"""Shared queryset behaviour: search and validated multi-field ordering."""

from collections.abc import Iterable, Mapping
from typing import Generic, TypeVar

from django.db import models
from djangoql.exceptions import DjangoQLError
from djangoql.queryset import apply_search
from djangoql.schema import DjangoQLSchema
from typing_extensions import Self

from ..utils.query import keywords_query

M = TypeVar("M", bound=models.Model)

DJANGOQL_MARKERS = ("=", "~", ">", "<", " in ", " and ", " or ")

# what a DjangoQL query may name: the chapters and their rows, nothing else
SEARCHABLE_MODELS = frozenset(
    {
        "app.chapter",
        "app.specialization",
        "app.faculty",
        "app.facultyspecialization",
        "app.employee",
        "app.contract",
    },
)


class DataSchema(DjangoQLSchema):
    """DjangoQL over the app's data only: never the users, the backups or the settings.

    The default schema follows every relation, so `chapter.backups.created_by.username`
    would be a query; here a relation to any other model does not exist.
    """

    def excluded(self, model: type[models.Model]) -> bool:  # noqa: D102
        return self.model_label(model) not in SEARCHABLE_MODELS


class BaseQuerySet(models.QuerySet, Generic[M]):
    """Base queryset: every model's queryset derives from it."""

    search_fields: tuple[str, ...] = ("name",)

    def search(self, value: str | None, fields: Iterable[str] | None = None) -> Self:
        """Filter by keywords (every word in any field), or by a DjangoQL query.

        A value holding a DjangoQL operator (`name ~ "sam" and is_active = True`) is tried
        as DjangoQL first; an invalid query falls back to plain keywords.

        Example:
            >>> Faculty.objects.search("comp sci")  # doctest: +SKIP
        """
        if not value or not value.strip():
            return self

        if any(marker in value.lower() for marker in DJANGOQL_MARKERS):
            try:
                return apply_search(self, value, schema=DataSchema)
            except (DjangoQLError, ValueError, TypeError):
                pass

        fields = tuple(fields or self.search_fields)

        found = self.filter(keywords_query(value, fields))

        # a field across a to-many relation can match a row more than once
        return found.distinct() if any("__" in field for field in fields) else found

    def order_by_fields(self, ordering: Iterable[str], allowed: Mapping[str, object]) -> Self:
        """Order by `ordering` (`-name`, `students`), keeping only fields in `allowed`."""
        valid = [field for field in ordering if field.lstrip("-") in allowed]

        if not valid:
            return self

        return self.order_by(*valid, "pk")

    def for_chapter(self, chapter_id: int | None) -> Self:
        """Rows owned by one chapter (every chapter-owned model has a `chapter` field)."""
        return self.filter(chapter_id=chapter_id)
