from ..querysets import SpecializationQuerySet
from .base import ChapterOwnedManager


class SpecializationManager(ChapterOwnedManager.from_queryset(SpecializationQuerySet)):  # type: ignore[misc]
    """Specializations: one accepted by a faculty or held by an employee cannot be deleted."""
