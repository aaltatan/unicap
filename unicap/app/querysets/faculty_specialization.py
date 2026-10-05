from .base import BaseQuerySet


class FacultySpecializationQuerySet(BaseQuerySet):
    """Accepted specializations (read with their faculty)."""

    search_fields = ("specialization__name",)
