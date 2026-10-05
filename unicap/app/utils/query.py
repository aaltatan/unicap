"""Query helpers shared by every queryset and filter."""

from collections.abc import Iterable

from django.db.models import Count, IntegerField, OuterRef, Q, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
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


def related_count(rows: QuerySet, outer: str) -> Coalesce:
    """How many of `rows` point at the outer row through their field `outer`: a subquery.

    Several `Count("relation", distinct=True)` in one query join every relation at once, so
    the database builds faculties x employees x contracts rows per chapter before counting.
    A count per subquery reads each relation once.

    Example:
        ```python
        Chapter.objects.annotate(employees_count=related_count(Employee.objects.all(), "chapter"))
        ```
    """
    counted = (
        rows.filter(**{outer: OuterRef("pk")})
        .order_by()
        .values(outer)
        .annotate(total=Count("pk"))
        .values("total")
    )

    return Coalesce(Subquery(counted, output_field=IntegerField()), 0)


def parse_ordering(value: str | None) -> list[str]:
    """`"-name,students"` -> `["-name", "students"]` (blank parts dropped).

    Example:
        >>> parse_ordering("-name, students,")
        ['-name', 'students']
    """
    if not value:
        return []

    return [part.strip() for part in value.split(",") if part.strip()]
