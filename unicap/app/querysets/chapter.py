from django.db.models import Prefetch
from typing_extensions import Self

from ..constants import chapter as constants
from ..utils.query import related_count
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
            "employees__excluded_faculties",
            "contracts",
        )

    def annotate_counts(self) -> Self:
        """How many faculties, employees and (signed) contracts each chapter holds."""
        faculties, employees, contracts = (
            self.model._meta.get_field(name).related_model.objects.all()  # noqa: SLF001
            for name in ("faculties", "employees", "contracts")
        )

        return self.annotate(
            faculties_count=related_count(faculties, "chapter"),
            employees_count=related_count(employees, "chapter"),
            contracts_count=related_count(contracts, "chapter"),
            signed_count=related_count(contracts.filter(faculty__isnull=False), "chapter"),
        )
