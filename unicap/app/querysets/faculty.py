from django.db.models import Count, Prefetch, Q
from typing_extensions import Self

from ..constants import faculty as constants
from .base import BaseQuerySet


class FacultyQuerySet(BaseQuerySet):
    """Faculties: their accepted specializations and counts."""

    search_fields = constants.SEARCH_FIELDS

    def with_shares(self) -> Self:
        """Prefetch the accepted specializations, in their order."""
        share = self.model._meta.get_field("shares").related_model  # noqa: SLF001

        return self.prefetch_related(
            Prefetch("shares", queryset=share.objects.select_related("specialization")),
        )

    def annotate_counts(self) -> Self:
        """Accepted specializations of each type, and contracts signed to the faculty."""
        return self.annotate(
            specialized_count=Count(
                "shares",
                filter=Q(shares__specialization_type="specialized"),
                distinct=True,
            ),
            supported_count=Count(
                "shares",
                filter=Q(shares__specialization_type="supported"),
                distinct=True,
            ),
            contracts_count=Count("contracts", distinct=True),
        )

    def accepting(self, specialization_id: int) -> Self:
        """Faculties accepting a specialization (specialized or supported)."""
        return self.filter(shares__specialization_id=specialization_id).distinct()
