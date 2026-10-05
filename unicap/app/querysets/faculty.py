from django.db.models import Prefetch
from typing_extensions import Self

from ..constants import faculty as constants
from ..utils.query import related_count
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
        shares, contracts = (
            self.model._meta.get_field(name).related_model.objects.all()  # noqa: SLF001
            for name in ("shares", "contracts")
        )

        return self.annotate(
            specialized_count=related_count(
                shares.filter(specialization_type="specialized"), "faculty"
            ),
            supported_count=related_count(
                shares.filter(specialization_type="supported"), "faculty"
            ),
            contracts_count=related_count(contracts, "faculty"),
        )

    def accepting(self, specialization_id: int) -> Self:
        """Faculties accepting a specialization (specialized or supported)."""
        return self.filter(shares__specialization_id=specialization_id).distinct()
