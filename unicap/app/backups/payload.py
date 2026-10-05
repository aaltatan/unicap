"""Backups as JSON: rows written and read by name, so they restore into any chapter.

A backup holds `chapters`, each with its settings and the sections it covers
(`specializations`, `faculties` with their shares, `employees`, `contracts`); a system
backup also holds the `settings`. Restoring a section makes it equal to the backup: its rows
are created or updated by name, and the rows the backup does not hold are removed.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from django.db import models
from django.utils.translation import gettext as _
from solo.models import SingletonModel

from ..exceptions import UserError
from ..managers.base import blocking_rows
from ..models import (
    AppSettings,
    Chapter,
    ChapterSettings,
    Contract,
    ContractSettings,
    Employee,
    EmployeeSettings,
    Faculty,
    FacultySettings,
    FacultySpecialization,
    Specialization,
    SpecializationSettings,
)

FORMAT = "unicap-backup"
VERSION = 1

# in dependency order: a section refers to the ones before it (by name)
SECTIONS = ("specializations", "faculties", "employees", "contracts")

CHAPTER_FIELDS = (
    "name",
    "max_students",
    "is_default",
    "notes",
)
SPECIALIZATION_FIELDS = ("name", "is_active", "notes")
FACULTY_FIELDS = (
    "name",
    "students_per_phd",
    "min_staff_percentage",
    "current_students",
    "target_students",
    "max_students",
    "min_specialized",
    "max_specialized",
    "min_supported",
    "max_supported",
    "max_share_rounding",
    "min_share_rounding",
    "staff_rounding",
    "masters_rounding",
    "notes",
)
SHARE_FIELDS = (
    "specialization_type",
    "percentage",
    "min_percentage",
    "max_percentage",
    "min_teachers",
    "max_teachers",
    "contract_type",
    "calculate_masters",
    "masters_per_phd",
    "position",
)
EMPLOYEE_FIELDS = ("name", "is_active", "notes")
CONTRACT_FIELDS = (
    "contract_type",
    "employment_type",
    "degree",
    "is_active",
    "position",
    "notes",
)

SETTINGS_MODELS: dict[str, type[SingletonModel]] = {
    "app": AppSettings,
    "chapters": ChapterSettings,
    "specializations": SpecializationSettings,
    "faculties": FacultySettings,
    "employees": EmployeeSettings,
    "contracts": ContractSettings,
}


# --- writing a backup ---------------------------------------------------------------------


def dump_chapter(chapter: Chapter, sections: Iterable[str] = SECTIONS) -> dict[str, Any]:
    """One chapter's settings and the `sections` asked for."""
    data = _fields(chapter, CHAPTER_FIELDS)

    for section in sections:
        data[section] = _DUMPERS[section](chapter)

    return data


def dump_settings() -> dict[str, Any]:
    """Every settings singleton's fields."""
    return {
        key: _fields(model.get_solo(), _setting_fields(model))
        for key, model in SETTINGS_MODELS.items()
    }


def _dump_specializations(chapter: Chapter) -> list[dict[str, Any]]:
    return [_fields(row, SPECIALIZATION_FIELDS) for row in chapter.specializations.order_by("name")]


def _dump_faculties(chapter: Chapter) -> list[dict[str, Any]]:
    faculties = chapter.faculties.order_by("name").prefetch_related("shares__specialization")

    return [
        {
            **_fields(faculty, FACULTY_FIELDS),
            "shares": [
                {"specialization": share.specialization.name, **_fields(share, SHARE_FIELDS)}
                for share in sorted(faculty.shares.all(), key=lambda share: share.position)
            ],
        }
        for faculty in faculties
    ]


def _dump_employees(chapter: Chapter) -> list[dict[str, Any]]:
    return [
        {
            **_fields(row, EMPLOYEE_FIELDS),
            "specialization": row.specialization.name,
            "excluded_faculties": sorted(f.name for f in row.excluded_faculties.all()),
        }
        for row in chapter.employees.select_related("specialization")
        .prefetch_related("excluded_faculties")
        .order_by("name")
    ]


def _dump_contracts(chapter: Chapter) -> list[dict[str, Any]]:
    contracts = chapter.contracts.select_related("employee", "faculty").order_by("position", "pk")

    return [
        {
            "employee": row.employee.name,
            "faculty": row.faculty.name if row.faculty else None,
            **_fields(row, CONTRACT_FIELDS),
        }
        for row in contracts
    ]


_DUMPERS = {
    "specializations": _dump_specializations,
    "faculties": _dump_faculties,
    "employees": _dump_employees,
    "contracts": _dump_contracts,
}


# --- checking a file ----------------------------------------------------------------------

# what a row of each section cannot go without: the names it is found by
_REQUIRED = {
    "specializations": ("name",),
    "faculties": ("name",),
    "employees": ("name", "specialization"),
    "contracts": ("employee",),
}


def check_chapter(data: object) -> None:
    """A chapter of an uploaded file has the shape `load_chapter` reads.

    Only the shape: a named chapter, sections that are lists of rows, each row holding the
    names it is found by. The values are checked when they are saved.

    Raises:
        UserError: naming what is missing, and where.
    """
    if not isinstance(data, dict) or not _is_name(data.get("name")):
        raise UserError(_("this backup is incomplete: a chapter has no name."))

    for section in SECTIONS:
        if section in data:
            _check_rows(data[section], section, _REQUIRED[section])

    for faculty in data.get("faculties", ()):
        if "shares" in faculty:
            _check_rows(faculty["shares"], "faculties", ("specialization",))


def _check_rows(rows: object, section: str, required: Iterable[str]) -> None:
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        msg = _("this backup is incomplete: %(section)s is not a list of rows.") % {
            "section": _(section),
        }
        raise UserError(msg)

    for number, row in enumerate(rows, start=1):
        if missing := [key for key in required if not _is_name(row.get(key))]:
            msg = _("this backup is incomplete: %(section)s, row %(row)s has no %(fields)s.") % {
                "section": _(section),
                "row": number,
                "fields": ", ".join(missing),
            }
            raise UserError(msg)


def _is_name(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


# --- restoring ----------------------------------------------------------------------------


def load_chapter(chapter: Chapter, data: Mapping[str, Any], *, settings: bool) -> None:
    """Make `chapter`'s sections held by `data` equal to it (and its settings, if `settings`).

    Rows are written first, in dependency order; the rows to remove go last, in reverse
    order (contracts before the employees they belong to, ...). Run it inside
    `Chapter.objects.validated(chapter.pk)`.

    Raises:
        UserError: a row refers to a name that is not there, or a removed row is still used.
    """
    if settings:
        for field in CHAPTER_FIELDS:
            if field in data and field not in ("name", "is_default"):
                setattr(chapter, field, data[field])
        chapter.save()

    sections = [section for section in SECTIONS if section in data]

    kept = {section: _LOADERS[section](chapter, data[section]) for section in sections}

    for section in reversed(sections):
        _prune(chapter, section, kept[section])


def load_settings(data: Mapping[str, Any]) -> None:
    """Write every settings singleton held by `data`."""
    for key, model in SETTINGS_MODELS.items():
        if key not in data:
            continue

        row = model.get_solo()

        for field in _setting_fields(model):
            if field in data[key]:
                setattr(row, field, data[key][field])

        row.save()


def _load_specializations(chapter: Chapter, rows: list[dict[str, Any]]) -> set[str]:
    for row in rows:
        _upsert(Specialization, chapter, {"name": row["name"]}, row, SPECIALIZATION_FIELDS)

    return {row["name"] for row in rows}


def _load_faculties(chapter: Chapter, rows: list[dict[str, Any]]) -> set[str]:
    specializations = _by_name(chapter.specializations.all())

    for row in rows:
        faculty = _upsert(Faculty, chapter, {"name": row["name"]}, row, FACULTY_FIELDS)

        faculty.shares.all().delete()

        for share in row.get("shares", []):
            FacultySpecialization.objects.create(
                faculty=faculty,
                specialization=_named(specializations, share["specialization"], row["name"]),
                **{field: share[field] for field in SHARE_FIELDS if field in share},
            )

    return {row["name"] for row in rows}


def _load_employees(chapter: Chapter, rows: list[dict[str, Any]]) -> set[str]:
    specializations = _by_name(chapter.specializations.all())
    faculties = _by_name(chapter.faculties.all())

    for row in rows:
        specialization = _named(specializations, row["specialization"], row["name"])
        employee = _upsert(
            Employee,
            chapter,
            {"name": row["name"]},
            {**row, "specialization": specialization},
            (*EMPLOYEE_FIELDS, "specialization"),
        )
        # a backup made before the constraint existed holds none
        employee.excluded_faculties.set(
            _named(faculties, name, row["name"]) for name in row.get("excluded_faculties", ())
        )

    return {row["name"] for row in rows}


def _load_contracts(chapter: Chapter, rows: list[dict[str, Any]]) -> set[str]:
    employees = _by_name(chapter.employees.all())
    faculties = _by_name(chapter.faculties.all())

    for row in rows:
        employee = _named(employees, row["employee"], row["employee"])
        faculty = _named(faculties, row["faculty"], row["employee"]) if row.get("faculty") else None
        _upsert(
            Contract,
            chapter,
            {"employee": employee},
            {**row, "faculty": faculty},
            (*CONTRACT_FIELDS, "faculty"),
        )

    return {row["employee"] for row in rows}


_LOADERS = {
    "specializations": _load_specializations,
    "faculties": _load_faculties,
    "employees": _load_employees,
    "contracts": _load_contracts,
}

_PRUNED = {
    "specializations": ("specializations", "name"),
    "faculties": ("faculties", "name"),
    "employees": ("employees", "name"),
    "contracts": ("contracts", "employee__name"),
}


def _prune(chapter: Chapter, section: str, kept: set[str]) -> None:
    """Remove the section's rows the backup does not hold."""
    related, key = _PRUNED[section]

    removed = getattr(chapter, related).exclude(**{f"{key}__in": kept})
    names = sorted(removed.values_list(key, flat=True))

    if section == "faculties":
        # the backup says these faculties are gone: their contracts go back to unsigned
        # (a user cannot delete a faculty with contracts; a restore replaces the section)
        chapter.contracts.filter(faculty__in=removed).update(faculty=None)

    try:
        removed.delete()
    except (models.ProtectedError, models.RestrictedError) as error:
        rows = blocking_rows(error)
        msg = _(
            "%(section)s: %(names)s cannot be removed, still used by %(users)s; "
            "restore the whole chapter instead.",
        ) % {
            "section": _(section),
            "names": ", ".join(names[:5]),
            "users": ", ".join(sorted({str(row) for row in rows})[:5]),
        }
        raise UserError(msg) from error


def _upsert(
    model: type[models.Model],
    chapter: Chapter,
    lookup: Mapping[str, Any],
    row: Mapping[str, Any],
    fields: Iterable[str],
) -> Any:  # noqa: ANN401 - the row of whichever section's model
    values = {field: row[field] for field in fields if field in row}
    instance, _created = model._default_manager.update_or_create(  # noqa: SLF001
        chapter=chapter, **lookup, defaults=values
    )
    return instance


def _by_name(rows: Iterable[Any]) -> dict[str, Any]:
    return {row.name: row for row in rows}


def _named(rows: Mapping[str, models.Model], name: str, owner: str) -> models.Model:
    if (row := rows.get(name)) is None:
        msg = _("%(owner)s: no %(name)s in this chapter; restore it first.") % {
            "owner": owner,
            "name": name,
        }
        raise UserError(msg)
    return row


def _fields(row: models.Model, fields: Iterable[str]) -> dict[str, Any]:
    return {field: getattr(row, field) for field in fields}


def _setting_fields(model: type[models.Model]) -> list[str]:
    return [
        field.name
        for field in model._meta.concrete_fields  # noqa: SLF001
        if not field.primary_key
    ]
