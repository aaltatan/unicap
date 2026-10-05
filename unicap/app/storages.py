"""Where files that must not be served are kept."""

from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateStorage(FileSystemStorage):
    """Files under `PRIVATE_MEDIA_ROOT`: no URL, so only a view (and its permission) hands them out.

    `MEDIA_ROOT` is served as it is (by the web server, or by Django while developing): a
    backup there could be downloaded by anyone who guesses its name. The folder is read
    from the settings each time, so tests can point it elsewhere.

    Example:
        ```python
        file = models.FileField(upload_to="backups/", storage=PrivateStorage())
        ```
    """

    @property
    def base_location(self) -> str:  # type: ignore[override]
        """The private folder, as the settings name it now."""
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self) -> str:  # type: ignore[override]
        """The private folder's absolute path."""
        return str(Path(self.base_location).resolve())

    @property
    def base_url(self) -> None:  # type: ignore[override]
        """None: `url()` raises, a private file has no address."""
        return
