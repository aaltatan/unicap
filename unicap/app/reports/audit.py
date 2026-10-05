"""The calculation audit: how each capacity is reached, one step after the other.

Nothing is computed here: every result is the domain's (`FacultyReport`, `ChapterReport`).
A step only shows the numbers the domain worked with, written as the operation it did
(`33 × 20`), beside the rule it follows, so an auditor can redo it by hand.
"""

# ruff: noqa: RUF001, RUF002 - the operations are written with their own signs

from collections import Counter
from typing import TYPE_CHECKING, Any

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from unicap.domain import ChapterReport, FacultyReport

from ..choices import RoundingChoices
from ..templatetags.domain import status_label, terms
from ..templatetags.utils import number, percent
from .context import capacity_context

if TYPE_CHECKING:
    from ..models import Chapter

# the ministry's counting rules, as the domain applies them (`unicap.domain.capacity`)
RULES = (
    gettext_lazy(
        "A contract whose specialization the faculty does not accept is never counted, nor one "
        "of an employee who cannot be counted in that faculty.",
    ),
    gettext_lazy(
        "Parttime PhDs of a type (specialized / supported) are counted up to the number of "
        "counted fulltime PhDs (staff and borrowed) of the same type.",
    ),
    gettext_lazy(
        "A specialization is counted up to its max share of all counted teachers and up to "
        "its max teachers, and each type up to the faculty's max specialized / supported PhDs. "
        "Masters are left out first, then parttime, then borrowed, then staff.",
    ),
    gettext_lazy(
        "Masters are counted up to the number of counted specialized fulltime PhDs; a "
        "specialization's masters per PhD says how many masters make one PhD, and the "
        "faculty's masters rounding how that rounds to whole PhDs.",
    ),
    gettext_lazy(
        "Fulltime staff must be at least the min staff percentage of all PhDs signed to the "
        "faculty, the uncounted ones included.",
    ),
    gettext_lazy(
        "A specialization below its min share or min teachers is a violation: a minimum "
        "never leaves anyone out.",
    ),
    gettext_lazy("More current students than the capacity is a violation."),
    gettext_lazy(
        "Capacity = counted PhD equivalents × students per PhD, capped by the faculty's max "
        "students. The chapter's capacity is its faculties' capacities summed, capped by its "
        "own max students.",
    ),
    gettext_lazy(
        "When several contracts compete for a place, the ones signed last are the ones not "
        "counted. Every maximum is applied again until none leaves anyone out.",
    ),
)

Step = dict[str, Any]


def audit_context(chapter: "Chapter", report: ChapterReport) -> dict[str, Any]:
    """The capacity report, with the steps behind every faculty's and the chapter's numbers.

    Example:
        ```python
        audit_context(chapter, report)["faculties"][0]["steps"][0]["value"]
        ```
    """
    context = capacity_context(chapter, report)

    for row, faculty in zip(context["faculties"], report.faculties, strict=True):
        row["steps"] = _numbered(_faculty_steps(faculty))
        row["uncounted"] = _uncounted_rows(faculty)

    return {
        **context,
        "rules": [str(rule) for rule in RULES],
        "steps": _numbered(_chapter_steps(report)),
    }


def _faculty_steps(report: FacultyReport) -> list[Step]:
    faculty, counted, signed = report.faculty, report.counted, report.calculation.signed_roster

    signed_phds = signed.phds + signed.unaccepted_phds
    uncounted = Counter(status_label(report.statuses[contract]) for contract in report.uncounted)
    reasons = "; ".join(f"{reason}: {count}" for reason, count in uncounted.items())

    steps = [
        _step(_("contracts signed to the faculty"), "", len(report.statuses)),
        _step(
            _("left out of the calculation"),
            _("switched off, or masters the faculty does not calculate"),
            len(report.excluded),
        ),
        _step(
            _("in the calculation"),
            f"{len(report.statuses)} - {len(report.excluded)}",
            len(report.included),
        ),
        _step(_("not counted (rules 1 to 4)"), reasons, len(report.uncounted)),
        _step(
            _("counted teachers"),
            f"{len(report.included)} - {len(report.uncounted)}",
            len(report.counted_contracts),
        ),
        _step(
            _("counted PhDs"),
            _(
                "specialized %(specialized)s (fulltime staff %(sfs)s + fulltime borrowed %(sfb)s "
                "+ parttime %(sp)s) + supported %(supported)s (fulltime staff %(ufs)s + fulltime "
                "borrowed %(ufb)s + parttime %(up)s)"
            )
            % {
                "specialized": counted.specialized_fulltime + counted.specialized_parttime,
                "sfs": counted.specialized_fulltime_staff,
                "sfb": counted.specialized_fulltime_borrowed,
                "sp": counted.specialized_parttime,
                "supported": counted.supported_fulltime + counted.supported_parttime,
                "ufs": counted.supported_fulltime_staff,
                "ufb": counted.supported_fulltime_borrowed,
                "up": counted.supported_parttime,
            },
            counted.phds,
        ),
        _step(
            _("counted masters, as PhDs"),
            _(
                "%(masters)s masters, each specialization's by its masters per PhD, summed "
                "then rounded %(rounding)s"
            )
            % {
                "masters": counted.masters,
                "rounding": RoundingChoices(faculty.masters_rounding.value).label,
            },
            counted.masters_as_phds,
        ),
        _step(
            _("PhD equivalents"),
            f"{counted.phds} + {counted.masters_as_phds}",
            counted.phd_equivalents,
        ),
        _step(
            _("teaching capacity"),
            _("%(phds)s PhD equivalents × %(students)s students per PhD")
            % {"phds": counted.phd_equivalents, "students": faculty.students_per_phd},
            report.teaching_capacity,
        ),
        _step(
            _("capacity"),
            _("no max students: the teaching capacity")
            if faculty.max_students is None
            else _("the smaller of the teaching capacity %(teaching)s and the max students %(max)s")
            % {"teaching": report.teaching_capacity, "max": faculty.max_students},
            report.capacity,
        ),
        _step(
            _("staff percentage"),
            _("%(staff)s fulltime staff ÷ %(phds)s signed PhDs × 100 (minimum %(minimum)s%%)")
            % {
                "staff": signed.fulltime_staff,
                "phds": signed_phds,
                "minimum": number(faculty.min_staff_percentage),
            },
            percent(report.staff_percentage, 1),
        ),
    ]

    if faculty.current_students is not None:
        steps.append(
            _step(
                _("free seats"),
                _("capacity %(capacity)s - current students %(current)s")
                % {"capacity": report.capacity, "current": faculty.current_students},
                report.free_seats,
            )
        )

    return steps


def _chapter_steps(report: ChapterReport) -> list[Step]:
    capacities = " + ".join(str(faculty.capacity) for faculty in report.faculties)
    maximum = report.chapter.max_students

    steps = [
        _step(_("the faculties' capacities summed"), capacities, report.faculties_capacity),
        _step(
            _("chapter capacity"),
            _("no chapter max students: the sum")
            if maximum is None
            else _("the smaller of the sum %(sum)s and the chapter's max students %(max)s")
            % {"sum": report.faculties_capacity, "max": maximum},
            report.capacity,
        ),
    ]

    if report.current_students is not None:
        steps.append(
            _step(
                _("free seats"),
                _("chapter capacity %(capacity)s - current students %(current)s")
                % {"capacity": report.capacity, "current": report.current_students},
                report.free_seats,
            )
        )

    return steps


def _uncounted_rows(report: FacultyReport) -> list[dict[str, Any]]:
    """Every contract signed to the faculty that is not counted, and why (in staff order)."""
    return [
        {
            "index": index,
            "name": contract.employee.name,
            "specialization": contract.employee.specialization.name,
            "terms": terms(contract),
            "reason": status_label(status),
        }
        for index, (contract, status) in enumerate(
            ((c, s) for c, s in report.in_staff_order if not s.is_counted), 1
        )
    ]


def _step(label: str, how: str, value: object) -> Step:
    return {"label": label, "how": how, "value": str(value)}


def _numbered(steps: list[Step]) -> list[Step]:
    return [{"index": index, **step} for index, step in enumerate(steps, 1)]
