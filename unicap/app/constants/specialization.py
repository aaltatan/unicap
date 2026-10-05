from django.utils.translation import gettext_lazy as _

from ..utils import StrOrPromise

ORDERING_FIELDS: dict[str, StrOrPromise] = {
    "name": _("name"),
    "is_active": _("is active"),
    "faculties_count": _("faculties"),
    "employees_count": _("employees"),
    "notes": _("notes"),
}

SEARCH_FIELDS: tuple[str, ...] = ("name", "notes")
