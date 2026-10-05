"""Values every template receives: the app settings, the sidebar and the chapters."""

from dataclasses import dataclass, replace
from typing import Any

from django.http import HttpRequest
from django.urls import reverse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from unicap.app.models import AppSettings, Chapter, User


@dataclass(frozen=True)
class NavLink:
    url_name: str
    text: str | Promise
    icon: str
    permission: str | None = None
    superuser: bool = False  # only for admins (the admin panel)
    create_url_name: str | None = None  # its "new" form, opened from the sidebar
    create_permission: str | None = None

    @property
    def url(self) -> str:
        return reverse(self.url_name)

    @property
    def create_url(self) -> str | None:
        return reverse(self.create_url_name) if self.create_url_name else None


@dataclass(frozen=True)
class NavSection:
    title: str | Promise
    links: tuple[NavLink, ...]


@dataclass(frozen=True)
class Crumb:
    """A step of the header's breadcrumb, above the page shown (`url` None: only a label)."""

    text: str | Promise
    url: str | None = None


NAVIGATION = (
    NavSection(
        _("overview"),
        (
            NavLink("board:dashboard", _("dashboard"), "chart-pie"),
            NavLink("board:index", _("board"), "view-columns", "app.view_contract"),
        ),
    ),
    NavSection(
        _("reports"),
        (
            NavLink(
                "reports:capacity", _("capacity report"), "document-chart-bar", "app.view_faculty"
            ),
            NavLink("reports:audit", _("calculation audit"), "calculator", "app.view_faculty"),
            NavLink(
                "reports:faculties",
                _("faculty reports"),
                "clipboard-document-list",
                "app.view_faculty",
            ),
        ),
    ),
    NavSection(
        _("data"),
        (
            NavLink(
                "hr:contracts:index",
                _("contracts"),
                "document-text",
                "app.view_contract",
                create_url_name="hr:contracts:create",
                create_permission="app.add_contract",
            ),
            NavLink(
                "hr:employees:index",
                _("employees"),
                "users",
                "app.view_employee",
                create_url_name="hr:employees:create",
                create_permission="app.add_employee",
            ),
            NavLink(
                "edu:faculties:index",
                _("faculties"),
                "building-library",
                "app.view_faculty",
                create_url_name="edu:faculties:create",
                create_permission="app.add_faculty",
            ),
            NavLink(
                "edu:specializations:index",
                _("specializations"),
                "academic-cap",
                "app.view_specialization",
                create_url_name="edu:specializations:create",
                create_permission="app.add_specialization",
            ),
        ),
    ),
    NavSection(
        _("settings"),
        (
            NavLink(
                "chapters:index",
                _("chapters"),
                "rectangle-stack",
                "app.view_chapter",
                create_url_name="chapters:create",
                create_permission="app.add_chapter",
            ),
            NavLink("backups:index", _("backups"), "archive-box", "app.view_backup"),
            NavLink("admin:index", _("admin panel"), "cog-6-tooth", superuser=True),
        ),
    ),
)


def constants(request: HttpRequest) -> dict[str, Any]:
    """Context processor: the app settings, the sidebar, the chapters and the current one."""
    app_settings = AppSettings.get_solo()

    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return {"app_settings": app_settings, "project_name": app_settings.project_name}

    navigation = [
        {
            "title": section.title,
            "links": [_for_user(user, link) for link in section.links if _allowed(user, link)],
        }
        for section in NAVIGATION
    ]

    return {
        "app_settings": app_settings,
        "project_name": app_settings.project_name,
        "navigation": [section for section in navigation if section["links"]],
        "breadcrumbs": breadcrumbs(request.path, navigation),
        "chapters": Chapter.objects.only("pk", "name", "is_default"),
        "current_chapter": getattr(request, "chapter", None),
    }


def breadcrumbs(path: str, navigation: list[dict[str, Any]]) -> list[Crumb]:
    """Where `path` is in the sidebar, above the page itself: its section, then its link.

    The link is left out on its own page (the page's title follows the crumbs); a page
    under no link has no crumb.

    Example:
        ```python
        breadcrumbs("/reports/capacity/pivot/", navigation)
        # [Crumb("reports"), Crumb("capacity report", "/reports/capacity/")]
        ```
    """
    found = [
        (section["title"], link)
        for section in navigation
        for link in section["links"]
        if _is_under(path, link.url)
    ]

    if not found:
        return []

    title, link = max(found, key=lambda item: len(item[1].url))

    section = Crumb(title)

    return [section] if path == link.url else [section, Crumb(link.text, link.url)]


def _is_under(path: str, url: str) -> bool:
    """`path` is the link's page or below it (the dashboard, at the root, only itself)."""
    return path == url if url == "/" else path.startswith(url)


def _for_user(user: "User", link: NavLink) -> NavLink:
    """The link, without its "new" button when the user may not add."""
    if link.create_permission is None or user.has_perm(link.create_permission):
        return link

    return replace(link, create_url_name=None)


def _allowed(user: "User", link: NavLink) -> bool:
    if link.superuser:
        return bool(user.is_superuser)

    return link.permission is None or user.has_perm(link.permission)
