from django.db.models import Count, Prefetch, Q
from typing_extensions import Self

from ..constants import chapter as constants
from .base import BaseQuerySet


class ChapterQuerySet(BaseQuerySet):
    """Chapters: counts of their rows, and everything `to_domain` reads."""

    search_fields = constants.SEARCH_FIELDS

    def with_domain_relations(self) -> Self:
        """Prefetch every owned row `Chapter.to_domain` reads (a handful of queries in all).

        Related models are reached through the relations, so this app never imports the
        apps that own them.
        """
        faculty = self.model._meta.get_field("faculties").related_model  # noqa: SLF001
        share = faculty._meta.get_field("shares").related_model  # noqa: SLF001

        return self.prefetch_related(
            "specializations",
            Prefetch(
                "faculties",
                queryset=faculty.objects.prefetch_related(
                    Prefetch("shares", queryset=share.objects.select_related("specialization")),
                ),
            ),
            "employees__specialization",
            "employees__excluded_faculties",
            "contracts",
        )

    def annotate_counts(self) -> Self:
        """How many faculties, employees and (signed) contracts each chapter holds."""
        return self.annotate(
            faculties_count=Count("faculties", distinct=True),
            employees_count=Count("employees", distinct=True),
            contracts_count=Count("contracts", distinct=True),
            signed_count=Count(
                "contracts",
                filter=Q(contracts__faculty__isnull=False),
                distinct=True,
            ),
        )
