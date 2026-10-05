from ..querysets import FacultySpecializationQuerySet
from .base import BaseManager


class FacultySpecializationManager(BaseManager.from_queryset(FacultySpecializationQuerySet)):  # type: ignore[misc]
    """Accepted specializations: written with their faculty (`Faculty.objects.save_with_shares`)."""
