from django.utils.translation import gettext_lazy as _

from ..utils import StrOrPromise

ORDERING_FIELDS: dict[str, StrOrPromise] = {
    "name": _("name"),
    "max_students": _("max students"),
    "faculties_count": _("faculties"),
    "employees_count": _("employees"),
    "contracts_count": _("contracts"),
    "created_at": _("created at"),
}

SEARCH_FIELDS: tuple[str, ...] = ("name", "notes")
