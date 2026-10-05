"""What a Word template can show: the domain's report as plain, translated, formatted values.

Nothing is computed here: every number comes from the domain's `ChapterReport` /
`FacultyReport`; this only names, labels and formats them for docxtpl (`{{ chapter.name }}`,
`{%tr for f in faculties %}`, ...). `VARIABLES` documents them for the people editing templates.
"""

from typing import TYPE_CHECKING, Any

from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from unicap.domain import (
    ChapterReport,
    Contract,
    ContractStatus,
    FacultyReport,
    HeadCount,
    Mix,
    SpecializationType,
)
from unicap.domain.capacity import roster_of

from ..choices import DegreeChoices, ReportChoices, SpecializationTypeChoices
from ..templatetags.domain import specialization_type, status_label, teacher_names, terms
from ..templatetags.utils import number, percent
from ..texts import violation_text

if TYPE_CHECKING:
    from ..models import Chapter, Faculty

HEAD_COUNTS = (
    ("specialized_fulltime_staff", gettext_lazy("specialized fulltime staff")),
    ("specialized_fulltime_borrowed", gettext_lazy("specialized fulltime borrowed")),
    ("specialized_parttime", gettext_lazy("specialized parttime")),
    ("supported_fulltime_staff", gettext_lazy("supported fulltime staff")),
    ("supported_fulltime_borrowed", gettext_lazy("supported fulltime borrowed")),
    ("supported_parttime", gettext_lazy("supported parttime")),
    ("masters", gettext_lazy("masters")),
)

# a pivot's columns: what a PhD's contract is (masters have a column of their own)
TERMS = (
    ("fulltime_staff", gettext_lazy("fulltime staff")),
    ("fulltime_borrowed", gettext_lazy("fulltime borrowed")),
    ("parttime", gettext_lazy("parttime")),
)

# the signed teachers as percentages (the domain's `Mix`), in pairs adding up to 100
MIX = (
    ("specialized", gettext_lazy("specialized")),
    ("supported", gettext_lazy("supported")),
    ("fulltime", gettext_lazy("fulltime")),
    ("parttime", gettext_lazy("parttime")),
    ("phds", gettext_lazy("PhDs")),
    ("masters", gettext_lazy("masters")),
)

_HEAD_COUNT_KEYS = ", ".join(key for key, _label in HEAD_COUNTS)
_MIX_KEYS = ", ".join(key for key, _label in MIX)
_TERMS_KEYS = ", ".join(key for key, _label in TERMS)

VARIABLES = {
    ReportChoices.CAPACITY: f"""\
date                      today
chapter.name, chapter.max_students, chapter.capacity, chapter.faculties_capacity,
chapter.teaching_capacity, chapter.target_shortfall, chapter.compliance,
chapter.current_students, chapter.max_students_allowed, chapter.free_seats
faculties                 a list, one row each:  {{%tr for f in faculties %}} ... {{%tr endfor %}}
  f.index, f.name, f.students_per_phd, f.capacity, f.teaching_capacity,
  f.current_students, f.max_students, f.free_seats,
  f.staff_percentage, f.phd_equivalents, f.compliance, f.is_compliant,
  f.violations (a list of texts), f.staff_count
  f.counted.<count>, f.signed.<count>
  f.mix.<share>           its signed teachers as percentages
<count>                   {_HEAD_COUNT_KEYS}
<share>                   {_MIX_KEYS}""",
    ReportChoices.FACULTY_STAFF: f"""\
date                      today
chapter.name
faculty.name, faculty.capacity, faculty.teaching_capacity, faculty.staff_percentage,
faculty.min_staff_percentage, faculty.students_per_phd, faculty.current_students,
faculty.target_students, faculty.max_students, faculty.free_seats, faculty.phd_equivalents,
faculty.compliance, faculty.is_compliant, faculty.violations (a list of texts), faculty.notes
faculty.mix.<share>       its signed teachers as percentages: {_MIX_KEYS}
staff                     a list, one row each:  {{%tr for e in staff %}} ... {{%tr endfor %}}
  e.index, e.name, e.specialization, e.specialization_type, e.degree, e.terms, e.status,
  e.is_counted
staff_count, counted_count
head_counts               a list:  h.label, h.signed, h.counted
counted.<count>, signed.<count>
<count>                   {_HEAD_COUNT_KEYS}""",
    ReportChoices.CAPACITY_PIVOT: f"""\
date, chapter.*           as in the capacity report
faculties                 a list, each as in the capacity report (f.name, f.capacity, ...), plus:
  f.specialized.<terms>, f.supported.<terms>     its PhDs of each type
  f.masters, f.phds
  f.names.specialized.<terms>, f.names.supported.<terms>, f.names.masters   who they are
<terms>                   {_TERMS_KEYS}, total
a cell is the counted teachers, then the signed ones when some are not counted: 3 / 5""",
    ReportChoices.FACULTY_STAFF_PIVOT: f"""\
date, chapter.name, faculty.*    as in the faculty staff report
specializations           a list:  {{%tr for s in specializations %}} ... {{%tr endfor %}}
  s.index, s.name, s.type, s.<terms>, s.masters, s.total
totals.<terms>, totals.masters, totals.total
<terms>                   {_TERMS_KEYS}
a cell is the counted teachers, then the signed ones when some are not counted: 3 / 5""",
    ReportChoices.AUDIT: """\
date, chapter.*           as in the capacity report
rules                     a list of texts: the counting rules
steps                     the chapter's steps, a list:  s.index, s.label, s.how, s.value
faculties                 a list, each as in the capacity report (f.name, f.capacity, ...), plus:
  f.steps                 its steps, a list:  s.index, s.label, s.how, s.value
  f.uncounted             its contracts not counted, a list:
                          u.index, u.name, u.specialization, u.terms, u.reason""",
}


def capacity_context(chapter: "Chapter", report: ChapterReport) -> dict[str, Any]:
    """The chapter's capacity report: one row per faculty, in the board's order.

    Example:
        ```python
        capacity_context(chapter, snapshot.report())["faculties"][0]["capacity"]
        ```
    """
    return {
        "date": _today(),
        "chapter": {
            "name": chapter.name,
            "max_students": _blank(chapter.max_students),
            "capacity": report.capacity,
            "faculties_capacity": report.faculties_capacity,
            "teaching_capacity": report.teaching_capacity,
            "target_shortfall": report.target_shortfall,
            "current_students": _blank(report.current_students),
            "max_students_allowed": _blank(report.max_students),
            "free_seats": _blank(report.free_seats),
            "compliance": _compliance(
                report.is_compliant, sum(len(faculty.violations) for faculty in report.faculties)
            ),
        },
        "faculties": [
            _faculty_row(index, faculty) for index, faculty in enumerate(report.faculties, 1)
        ],
    }


def faculty_context(
    chapter: "Chapter", faculty: "Faculty", report: FacultyReport
) -> dict[str, Any]:
    """One faculty and its own staff: every contract signed to it, in staff order.

    `faculty` is the row (its settings and notes), `report` the domain's evaluation of it.
    """
    staff = [
        _staff_row(index, contract, status)
        for index, (contract, status) in enumerate(report.in_staff_order, 1)
    ]

    return {
        "date": _today(),
        "chapter": {"name": chapter.name},
        "faculty": {
            **_faculty_row(None, report),
            "min_staff_percentage": f"{number(faculty.min_staff_percentage)}%",
            "target_students": _blank(faculty.target_students),
            "notes": faculty.notes,
        },
        "staff": staff,
        "staff_count": len(staff),
        "counted_count": sum(row["is_counted"] for row in staff),
        "head_counts": _head_count_rows(report.signed, report.counted),
        "signed": _head_counts(report.signed),
        "counted": _head_counts(report.counted),
    }


def capacity_pivot_context(chapter: "Chapter", report: ChapterReport) -> dict[str, Any]:
    """The capacity report, each faculty's PhDs as a specialized / supported by terms table.

    Example:
        ```python
        capacity_pivot_context(chapter, report)["faculties"][0]["specialized"]["fulltime_staff"]
        ```
    """
    context = capacity_context(chapter, report)

    for row, faculty in zip(context["faculties"], report.faculties, strict=True):
        row.update(_type_rows(faculty.counted, faculty.signed))
        row["names"] = _cell_names(faculty)

    return context


def faculty_pivot_context(
    chapter: "Chapter", faculty: "Faculty", report: FacultyReport
) -> dict[str, Any]:
    """One faculty's teachers counted by specialization and terms, instead of listed by name."""
    counted = roster_of(report.faculty, report.counted_contracts)
    signed = roster_of(report.faculty, report.included)

    keys = [*(key for key, _label in TERMS), "masters"]

    rows = [
        {
            "index": index,
            "name": item.specialization.name,
            "type": _type_label(report.faculty.type_of(item.specialization)),
            **{
                key: _of(getattr(counted.of(item.specialization), key), getattr(item, key))
                for key in keys
            },
            "total": _of(counted.of(item.specialization).heads, item.heads),
        }
        for index, item in enumerate(signed.counts, 1)
    ]

    totals = {
        key: _of(
            sum(getattr(item, key) for item in counted.counts),
            sum(getattr(item, key) for item in signed.counts),
        )
        for key in keys
    }

    context = faculty_context(chapter, faculty, report)

    return {
        **context,
        "specializations": rows,
        "totals": {**totals, "total": _of(counted.heads, signed.heads)},
    }


def mix_values(mix: Mix) -> dict[str, str]:
    """A mix's percentages as texts: `{"specialized": "75%", "supported": "25%", ...}`."""
    return {key: percent(getattr(mix, key)) for key, _label in MIX}


def _type_rows(counted: HeadCount, signed: HeadCount) -> dict[str, Any]:
    """A faculty's PhDs by type (rows) and terms (columns), its masters and PhDs in all."""

    def row(kind: SpecializationType) -> dict[str, str]:
        pairs = {
            key: (getattr(counted, f"{kind.value}_{key}"), getattr(signed, f"{kind.value}_{key}"))
            for key, _label in TERMS
        }
        total = _of(sum(c for c, _s in pairs.values()), sum(s for _c, s in pairs.values()))

        return {**{key: _of(*pair) for key, pair in pairs.items()}, "total": total}

    return {
        **{kind.value: row(kind) for kind in SpecializationType},
        "masters": _of(counted.masters, signed.masters),
        "phds": _of(counted.phds, signed.phds),
    }


def _cell_names(report: FacultyReport) -> dict[str, Any]:
    """The teachers behind each pivot cell, one per line: the counted ones, then all signed."""
    names = teacher_names(report)

    def cell(key: str) -> str:
        counted, signed = names["counted"].get(key, ""), names["signed"].get(key, "")

        if counted == signed:
            return signed

        return f"{_('counted')}:\n{counted}\n\n{_('signed')}:\n{signed}"

    return {
        **{
            kind.value: {key: cell(f"{kind.value}_{key}") for key, _label in TERMS}
            for kind in SpecializationType
        },
        "masters": cell("masters"),
    }


def _of(counted: int, signed: int) -> str:
    """`3` when every signed teacher is counted, else `3 / 5` (counted / signed)."""
    return str(counted) if counted == signed else f"{counted} / {signed}"


def _type_label(kind: SpecializationType | None) -> str:
    """`specialized` / `supported`, translated (empty: neither)."""
    return str(SpecializationTypeChoices(kind.value).label) if kind else ""


def _faculty_row(index: int | None, report: FacultyReport) -> dict[str, Any]:
    return {
        "index": index,
        "name": report.faculty.name,
        "students_per_phd": report.faculty.students_per_phd,
        "capacity": report.capacity,
        "teaching_capacity": report.teaching_capacity,
        "current_students": _blank(report.faculty.current_students),
        "max_students": _blank(report.faculty.max_students),
        "free_seats": _blank(report.free_seats),
        "staff_percentage": percent(report.staff_percentage, 1),
        "mix": mix_values(report.mix),
        "phd_equivalents": number(report.counted.phd_equivalents),
        "is_compliant": report.is_compliant,
        "compliance": _compliance(report.is_compliant, len(report.violations)),
        "violations": [violation_text(violation) for violation in report.violations],
        "staff_count": len(report.statuses),
        "counted": _head_counts(report.counted),
        "signed": _head_counts(report.signed),
    }


def _staff_row(index: int, contract: Contract, status: ContractStatus) -> dict[str, Any]:
    return {
        "index": index,
        "name": contract.employee.name,
        "specialization": contract.employee.specialization.name,
        "specialization_type": _type_label(specialization_type(contract)),
        "degree": str(DegreeChoices(contract.degree.value).label),
        "terms": terms(contract),
        "status": status_label(status),
        "is_counted": status.is_counted,
    }


def _head_counts(counts: HeadCount) -> dict[str, str]:
    values = {key: str(getattr(counts, key)) for key, _label in HEAD_COUNTS}
    return {**values, "phd_equivalents": number(counts.phd_equivalents)}


def _head_count_rows(signed: HeadCount, counted: HeadCount) -> list[dict[str, str]]:
    rows = [
        {
            "label": str(label),
            "signed": str(getattr(signed, key)),
            "counted": str(getattr(counted, key)),
        }
        for key, label in HEAD_COUNTS
    ]
    total = {
        "label": _("PhD equivalents"),
        "signed": number(signed.phd_equivalents),
        "counted": number(counted.phd_equivalents),
    }
    return [*rows, total]


def _compliance(is_compliant: bool, violations: int) -> str:  # noqa: FBT001
    if is_compliant:
        return _("compliant")

    return f"{violations} {_('violations')}"


def _blank(value: object) -> str:
    """`—` for an empty number, else the number."""
    return "—" if value is None else str(value)


def _today() -> str:
    return formats.date_format(timezone.localdate(), "DATE_FORMAT")
