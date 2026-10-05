"""The admin panel: for admins (superusers) only; users work in the app."""

from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _


class AdminSite(admin.AdminSite):
    """Django's admin, opened to superusers only (staff status alone is not enough)."""

    site_header = _("administration")
    site_title = _("administration")
    index_title = _("administration")

    def has_permission(self, request: HttpRequest) -> bool:
        """Only an active superuser."""
        return request.user.is_active and request.user.is_superuser
