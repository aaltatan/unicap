"""Readable, translated text for the domain's values (`{% load domain %}`).

Only labels: every value shown was computed by the domain.
"""

from django import template
from django.utils.translation import gettext as _

from unicap.domain import (
    Contract,
    ContractStatus,
    FacultyReport,
    HireKind,
    Mix,
    SpecializationType,
)

from ..choices import (
    CONTRACT_STATUS_LABELS,
    ContractTypeChoices,
    DegreeChoices,
    EmploymentTypeChoices,
    HireKindChoices,
    SpecializationTypeChoices,
)
from ..texts import violation_text

register = template.Library()


@register.filter
def status_label(status: ContractStatus | None) -> str:
    """`counted`, `specialization above its max share`, ... or `unsigned`."""
    if status is None:
        return _("unsigned")

    return str(CONTRACT_STATUS_LABELS[status])


@register.filter
def status_class(status: ContractStatus | None) -> str:
    """The card / badge style for a status: counted, uncounted, excluded or unsigned."""
    if status is None:
        return "unsigned"

    if status.is_excluded:
        return "excluded"

    return "counted" if status.is_counted else "uncounted"


@register.filter
def status_badge(status: ContractStatus | None) -> str:
    """The badge style for a status."""
    return {
        "counted": "badge-success",
        "uncounted": "badge-danger",
        "excluded": "badge-neutral",
        "unsigned": "badge-neutral",
    }[status_class(status)]


@register.filter
def terms(contract: Contract) -> str:
    """`fulltime staff`, `parttime borrowed` or `master`."""
    if not contract.is_phd:
        return str(DegreeChoices.MASTER.label)

    kind = ContractTypeChoices(contract.contract_type.value).label
    employment = EmploymentTypeChoices(contract.employment_type.value).label

    return f"{kind} {employment}"


@register.filter
def short_terms(contract: Contract) -> str:
    """`FT staff`, `FT borrowed`, `PT` or `MA`: fits on a one-line board card."""
    if not contract.is_phd:
        return _("MA")

    if not contract.is_fulltime:
        return _("PT")

    return _("FT staff") if contract.is_staff else _("FT borrowed")


@register.filter
def type_label(kind: SpecializationType | str) -> str:
    """`specialized` / `supported`, translated."""
    return str(SpecializationTypeChoices(str(kind)).label)


@register.filter
def specialization_type(contract: Contract) -> SpecializationType | None:
    """What the contract's specialization is in its faculty (None: unsigned, or not accepted)."""
    faculty, specialization = contract.faculty, contract.employee.specialization

    if faculty is None or not faculty.accepts(specialization):
        return None

    return faculty.type_of(specialization)


@register.filter
def type_badge(kind: SpecializationType | str) -> str:
    """The badge style of `specialized` / `supported`."""
    is_specialized = str(kind) == SpecializationType.SPECIALIZED.value

    return "badge-info" if is_specialized else "badge-warning"


@register.filter
def mix_rows(mix: Mix) -> list[dict[str, object]]:
    """A mix as pairs to draw: specialized / supported, fulltime / parttime, PhDs / masters."""
    pairs = (
        (SpecializationTypeChoices.SPECIALIZED.label, "specialized", "supported"),
        (ContractTypeChoices.FULLTIME.label, "fulltime", "parttime"),
        (_("PhDs"), "phds", "masters"),
    )
    labels = {
        "supported": SpecializationTypeChoices.SUPPORTED.label,
        "parttime": ContractTypeChoices.PARTTIME.label,
        "masters": _("masters"),
    }

    return [
        {
            "label": str(label),
            "value": getattr(mix, first),
            "other_label": str(labels[second]),
            "other_value": getattr(mix, second),
        }
        for label, first, second in pairs
    ]


@register.filter
def mix_text(mix: Mix) -> str:
    """`specialized 75% · supported 25%`, one pair per line: a tooltip beside the staff %."""
    return "\n".join(
        f"{row['label']} {float(row['value']):.0f}% · {row['other_label']} "
        f"{float(row['other_value']):.0f}%"
        for row in mix_rows(mix)
    )


@register.filter
def teacher_names(report: FacultyReport) -> dict[str, dict[str, str]]:
    """The teachers behind each head count, one name per line: tooltips for a report's numbers.

    `{"counted": {"specialized_fulltime_staff": <names>, ...}, "signed": {...}}`,
    in staff order, numbered from 1; `all` holds every head count's teachers together.
    """
    names: dict[str, dict[str, list[str]]] = {"counted": {}, "signed": {}}

    for contract, status in report.in_staff_order:
        key = _head_count_key(contract)

        if key is None or status.is_excluded:
            continue

        for group in ("signed", "counted") if status.is_counted else ("signed",):
            names[group].setdefault(key, []).append(contract.employee.name)
            names[group].setdefault("all", []).append(contract.employee.name)

    return {
        group: {key: _numbered(found) for key, found in by_key.items()}
        for group, by_key in names.items()
    }


def _numbered(names: list[str]) -> str:
    """`1. Dr. Hind`, `2. Dr. Omar`, ... one per line."""
    return "\n".join(f"{index}. {name}" for index, name in enumerate(names, 1))


def _head_count_key(contract: Contract) -> str | None:
    """Which of the seven head counts a contract is in (None: it is in none in its faculty)."""
    kind, faculty = specialization_type(contract), contract.faculty

    if kind is None or faculty is None or not contract.employee.can_be_counted_in(faculty):
        return None

    if not contract.is_phd:
        return "masters"

    if not contract.is_fulltime:
        return f"{kind.value}_parttime"

    return f"{kind.value}_fulltime_{'staff' if contract.is_staff else 'borrowed'}"


@register.filter
def named_type(contract: Contract) -> str:
    """`Dr. Hind (specialized)`: a teacher's name with their type, for titles (tooltips)."""
    kind = specialization_type(contract)

    return f"{contract.employee.name} ({type_label(kind)})" if kind else contract.employee.name


@register.filter
def signed_to(contract: Contract) -> str:
    """The faculty's name, or `unsigned`."""
    return contract.faculty.name if contract.faculty else _("unsigned")


@register.filter
def has_violation(report: object, kind: str) -> bool:
    """Whether the domain reported a violation of this kind (`staff_ratio_too_low`, ...)."""
    return any(violation.kind == kind for violation in getattr(report, "violations", ()))


register.filter("violation_text", violation_text)


@register.filter
def hire_kind_label(kind: HireKind | str) -> str:
    """`fulltime staff PhD`, `master`, ... translated."""
    return str(HireKindChoices(str(kind)).label)
