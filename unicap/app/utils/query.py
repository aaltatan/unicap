"""Query helpers shared by every queryset and filter."""

from collections.abc import Iterable

from django.db.models import Q, Value
from django.db.models.lookups import Contains

from .text import Normalized, search_terms


def keywords_query(value: str, fields: Iterable[str]) -> Q:
    """Every word of `value` must appear in at least one of `fields`, in any order.

    Words match inside words and ignore case, Arabic diacritics, spelling variants and a
    leading article: "هند عمار", "عمارة هندسة" and "هند عمراني" all find
    "هندسة العمارة والتخطيط العمراني". A word starting with `!` must appear in none.

    Example:
        ```python
        Specialization.objects.filter(keywords_query("هند عمار", ["name"]))
        ```
    """
    fields = tuple(fields)

    query = Q()

    for word in value.split():
        negated = word.startswith("!") and len(word) > 1

        for term in search_terms(word[1:] if negated else word):
            any_field = Q()

            for field in fields:
                any_field |= Q(Contains(Normalized(field), Value(term)))

            query &= ~any_field if negated else any_field

    return query


def parse_ordering(value: str | None) -> list[str]:
    """`"-name,students"` -> `["-name", "students"]` (blank parts dropped).

    Example:
        >>> parse_ordering("-name, students,")
        ['-name', 'students']
    """
    if not value:
        return []

    return [part.strip() for part in value.split(",") if part.strip()]
