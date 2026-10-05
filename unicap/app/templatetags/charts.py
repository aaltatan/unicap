"""Presentation helpers for charts (`{% load charts %}`): widths and labels, never values."""

from collections.abc import Iterable
from fractions import Fraction
from typing import Any

from django import template

from unicap.domain import EmploymentType, FacultyReport, TeacherKind

from ..choices import TEACHER_KIND_LABELS, EmploymentTypeChoices

register = template.Library()


@register.filter
def bar(value: float | Fraction | None, scale: float | None) -> str:
    """A bar's width in percent of `scale`, clipped to 0-100 (`style="width: {{ x|bar:max }}%"`)."""
    if not value or not scale:
        return "0"

    return f"{min(100.0, max(0.0, float(value) * 100 / float(scale))):.2f}"


@register.filter
def faculty_scale(lanes: Iterable[Any]) -> int:
    """The largest student number drawn among the lanes' faculties (the chart's full width)."""
    numbers = [
        number
        for lane in lanes
        for number in (
            lane.report.capacity,
            lane.report.teaching_capacity,
            lane.report.faculty.target_students,
            lane.report.faculty.max_students,
            lane.report.faculty.current_students,
        )
        if number
    ]

    return max(numbers, default=1)


@register.filter
def composition_chart(report: FacultyReport) -> dict[str, Any]:
    """A faculty's counted PhDs for its doughnut: kinds (outer ring), staff / borrowed (inner).

    Only labels and the domain's counts (`FacultyReport.composition`), masters left out of
    the chart; `json_script` it.
    """
    slices = [s for s in report.composition if s.kind is not TeacherKind.MASTER]

    groups = [
        {
            "employment": employment.value,
            "label": str(EmploymentTypeChoices(employment.value).label),
            "count": sum(s.count for s in slices if s.employment is employment),
        }
        for employment in EmploymentType
    ]

    return {
        "slices": [
            {
                "employment": s.employment.value,
                "kind": s.kind.value,
                "kind_label": str(TEACHER_KIND_LABELS[s.kind]),
                "label": f"{TEACHER_KIND_LABELS[s.kind]} · "
                f"{EmploymentTypeChoices(s.employment.value).label}",
                "count": s.count,
            }
            for s in slices
        ],
        "groups": [group for group in groups if group["count"]],
        "total": sum(s.count for s in slices),
    }
