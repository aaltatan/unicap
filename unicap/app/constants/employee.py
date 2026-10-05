from django.utils.translation import gettext_lazy as _

from ..utils import StrOrPromise

ORDERING_FIELDS: dict[str, StrOrPromise] = {
    "name": _("name"),
    "specialization__name": _("specialization"),
    "specialization_type": _("specialization type"),
    "is_active": _("is active"),
    "contract__faculty__name": _("faculty"),
    "notes": _("notes"),
}

SEARCH_FIELDS: tuple[str, ...] = ("name", "specialization__name", "notes")
