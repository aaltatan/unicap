"""Searching the whole app at once: the current chapter's rows, and the chapters."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from django.db.models import Model
from django.urls import reverse
from django.utils.functional import Promise
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from .models import Chapter, Contract, Employee, Faculty, Specialization, User

if TYPE_CHECKING:
    from .querysets.base import BaseQuerySet

LIMIT = 6


@dataclass(frozen=True)
class Group:
    """One kind of row found: the first ones, and how many in all."""

    title: str | Promise
    icon: str
    rows: list[Model]
    total: int
    table_url: str  # the table, searching the same words


@dataclass(frozen=True)
class _Kind:
    model: type[Model]
    permission: str
    title: str | Promise
    icon: str
    table: str
    owned: bool = True  # rows of a chapter


KINDS = (
    _Kind(Faculty, "app.view_faculty", _("faculties"), "building-library", "edu:faculties:index"),
    _Kind(
        Specialization,
        "app.view_specialization",
        _("specializations"),
        "academic-cap",
        "edu:specializations:index",
    ),
    _Kind(Employee, "app.view_employee", _("employees"), "users", "hr:employees:index"),
    _Kind(Contract, "app.view_contract", _("contracts"), "document-text", "hr:contracts:index"),
    _Kind(
        Chapter,
        "app.view_chapter",
        _("chapters"),
        "rectangle-stack",
        "chapters:index",
        owned=False,
    ),
)


def search_everything(user: User, chapter: Chapter | None, value: str) -> list[Group]:
    """Every kind of row the user may see, searched with the tables' search (any word order).

    Example:
        ```python
        search_everything(request.user, request.chapter, "هند عمار")
        ```
    """
    value = value.strip()

    if not value:
        return []

    groups = []

    for kind in KINDS:
        if not user.has_perm(kind.permission) or (kind.owned and chapter is None):
            continue

        rows = cast("BaseQuerySet", kind.model._default_manager.all())  # noqa: SLF001

        if kind.owned and chapter is not None:
            rows = rows.for_chapter(chapter.pk)

        found = rows.search(value)

        if total := found.count():
            groups.append(
                Group(
                    kind.title,
                    kind.icon,
                    list(found[:LIMIT]),
                    total,
                    f"{reverse(kind.table)}?{urlencode({'q': value})}",
                ),
            )

    return groups
