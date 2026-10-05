from ..querysets import BackupQuerySet
from .base import BaseManager


class BackupManager(BaseManager.from_queryset(BackupQuerySet)):  # type: ignore[misc]
    """Saved backups (written and restored by `backups.service`)."""
