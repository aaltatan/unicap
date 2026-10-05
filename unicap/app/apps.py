from django.apps import AppConfig
from django.contrib.admin import apps as admin_apps
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


class MainConfig(AppConfig):
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "unicap.app"
    label = "app"
    verbose_name = _("UniCap")

    def ready(self) -> None:
        """After every migrate: the roles (groups) exist with their permissions."""
        from .roles import ensure_roles  # noqa: PLC0415 - models are ready now

        post_migrate.connect(ensure_roles, sender=self, dispatch_uid="app.ensure_roles")


class UniCapAdminConfig(admin_apps.AdminConfig):
    """`django.contrib.admin` with the superusers-only site."""

    default = False
    default_site = "unicap.app.sites.AdminSite"
