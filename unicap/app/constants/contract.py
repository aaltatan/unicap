from django.utils.translation import gettext_lazy as _

from ..utils import StrOrPromise

ORDERING_FIELDS: dict[str, StrOrPromise] = {
    "position": _("signing order"),
    "employee__name": _("employee"),
    "employee__specialization__name": _("specialization"),
    "faculty__name": _("faculty"),
    "specialization_type": _("specialization type"),
    "degree": _("degree"),
    "contract_type": _("contract type"),
    "employment_type": _("employment type"),
    "is_active": _("is active"),
    "is_locked": _("locked"),
    "notes": _("notes"),
}

SEARCH_FIELDS: tuple[str, ...] = (
    "employee__name",
    "employee__specialization__name",
    "faculty__name",
    "notes",
)
