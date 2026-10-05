from typing import Literal

from django.utils.translation import gettext_lazy as _

from ..utils import StrOrPromise

ORDERING_FIELDS: dict[str, StrOrPromise] = {
    "name": _("name"),
    "students_per_phd": _("students per PhD"),
    "min_staff_percentage": _("min staff percentage"),
    "current_students": _("current students"),
    "target_students": _("target students"),
    "max_students": _("max students"),
    "specialized_count": _("specialized"),
    "supported_count": _("supported"),
    "contracts_count": _("contracts"),
    "notes": _("notes"),
}

SEARCH_FIELDS: tuple[str, ...] = ("name", "notes", "shares__specialization__name")

PREFETCH_RELATED_LOOKUPS = Literal["shares", "shares__specialization", "contracts"]
