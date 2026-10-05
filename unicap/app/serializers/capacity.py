"""The calculation API's input and output: numbers in, the domain's numbers out.

Only the shape is checked here; every rule (bounds, shares, ...) is the domain's, and a
broken one comes back as a 400 with the domain's message.
"""

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from unicap import domain

from ..choices import ContractTypeChoices, RoundingChoices, SpecializationTypeChoices
from ..texts import violation_text


def _percentage(**options: Any) -> serializers.FloatField:
    """A percentage field, 0 to 100 (used by the class bodies below, so it comes first)."""
    return serializers.FloatField(min_value=0, max_value=100, **options)


class SpecializationNumbersSerializer(serializers.Serializer):
    """One accepted specialization: its share, its bounds, and its teachers as numbers."""

    name = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(
        choices=SpecializationTypeChoices.choices,
        default=SpecializationTypeChoices.SPECIALIZED,
    )
    percentage = _percentage(required=False, allow_null=True)
    min_percentage = _percentage(required=False, allow_null=True)
    max_percentage = _percentage(required=False, allow_null=True)
    min_teachers = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_teachers = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    contract_type = serializers.ChoiceField(
        choices=ContractTypeChoices.choices, required=False, allow_null=True
    )
    calculate_masters = serializers.BooleanField(default=True)
    masters_per_phd = serializers.IntegerField(default=2, min_value=1)
    fulltime_staff = serializers.IntegerField(default=0, min_value=0)
    fulltime_borrowed = serializers.IntegerField(default=0, min_value=0)
    parttime = serializers.IntegerField(default=0, min_value=0)
    masters = serializers.IntegerField(default=0, min_value=0)


class FacultyNumbersSerializer(serializers.Serializer):
    """A faculty's numbers, and its accepted specializations with their teachers."""

    name = serializers.CharField(max_length=255)
    students_per_phd = serializers.IntegerField(min_value=1)
    min_staff_percentage = _percentage(default=50)
    current_students = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    target_students = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_students = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    min_specialized = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_specialized = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    min_supported = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_supported = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    max_share_rounding = serializers.ChoiceField(
        choices=RoundingChoices.choices, default=RoundingChoices.FLOOR
    )
    min_share_rounding = serializers.ChoiceField(
        choices=RoundingChoices.choices, default=RoundingChoices.CEILING
    )
    staff_rounding = serializers.ChoiceField(
        choices=RoundingChoices.choices, default=RoundingChoices.CEILING
    )
    masters_rounding = serializers.ChoiceField(
        choices=RoundingChoices.choices, default=RoundingChoices.FLOOR
    )
    specializations = SpecializationNumbersSerializer(many=True)

    def validate_specializations(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        names = [item["name"] for item in value]

        if repeated := sorted({name for name in names if names.count(name) > 1}):
            msg = _("each specialization is listed once: %(names)s") % {
                "names": ", ".join(repeated),
            }
            raise serializers.ValidationError(msg)

        return value


class CalculationRequestSerializer(serializers.Serializer):
    """A whole chapter as numbers.

    `count`: true (default) applies the ministry's counting rules to the numbers; false
    takes them as counted already and only calculates.
    """

    max_students = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    count = serializers.BooleanField(default=True)
    faculties = FacultyNumbersSerializer(many=True, allow_empty=False)

    def validate_faculties(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        names = [item["name"] for item in value]

        if repeated := sorted({name for name in names if names.count(name) > 1}):
            msg = _("each faculty is listed once: %(names)s") % {"names": ", ".join(repeated)}
            raise serializers.ValidationError(msg)

        return value

    def faculty_numbers(self) -> tuple[domain.FacultyNumbers, ...]:
        """Every faculty as the domain's numbers (DomainError: a broken rule)."""
        return tuple(_faculty_numbers(item) for item in self.validated_data["faculties"])


def report_data(report: domain.NumbersReport) -> dict[str, Any]:
    """The domain's results, as JSON-ready values (percentages as floats)."""
    return {
        "capacity": report.capacity,
        "faculties_capacity": report.faculties_capacity,
        "teaching_capacity": report.teaching_capacity,
        "max_students": report.max_students,
        "is_compliant": report.is_compliant,
        "faculties": [_calculation_data(item) for item in report.faculties],
    }


def _faculty_numbers(data: dict[str, Any]) -> domain.FacultyNumbers:
    rows = data["specializations"]

    specializations = {row["name"]: domain.Specialization(row["name"]) for row in rows}

    def of_type(kind: str) -> tuple[domain.Specialization, ...]:
        return tuple(specializations[row["name"]] for row in rows if row["type"] == kind)

    faculty = domain.ChapterFaculty(
        domain.Faculty(
            data["name"],
            specialized=of_type(SpecializationTypeChoices.SPECIALIZED),
            supported=of_type(SpecializationTypeChoices.SUPPORTED),
        ),
        students_per_phd=data["students_per_phd"],
        min_staff_percentage=data["min_staff_percentage"],
        current_students=data.get("current_students"),
        target_students=data.get("target_students"),
        max_students=data.get("max_students"),
        shares=tuple(
            domain.Share(
                specializations[row["name"]],
                percentage=row.get("percentage"),
                min_percentage=row.get("min_percentage"),
                max_percentage=row.get("max_percentage"),
                min_teachers=row.get("min_teachers"),
                max_teachers=row.get("max_teachers"),
                contract_type=domain.ContractType(kind)
                if (kind := row.get("contract_type"))
                else None,
                calculate_masters=row["calculate_masters"],
                masters_per_phd=row["masters_per_phd"],
            )
            for row in rows
        ),
        min_specialized=data.get("min_specialized"),
        max_specialized=data.get("max_specialized"),
        min_supported=data.get("min_supported"),
        max_supported=data.get("max_supported"),
        max_share_rounding=domain.RoundingMode(data["max_share_rounding"]),
        min_share_rounding=domain.RoundingMode(data["min_share_rounding"]),
        staff_rounding=domain.RoundingMode(data["staff_rounding"]),
        masters_rounding=domain.RoundingMode(data["masters_rounding"]),
    )

    teachers = domain.Roster(
        tuple(
            domain.SpecializationCount(
                specializations[row["name"]],
                fulltime_staff=row["fulltime_staff"],
                fulltime_borrowed=row["fulltime_borrowed"],
                parttime=row["parttime"],
                masters=row["masters"],
            )
            for row in rows
        )
    )

    return domain.FacultyNumbers(faculty, teachers)


def _calculation_data(item: domain.Calculation) -> dict[str, Any]:
    return {
        "name": item.faculty.name,
        "capacity": item.capacity,
        "teaching_capacity": item.teaching_capacity,
        "unused_teaching_capacity": item.unused_teaching_capacity,
        "phd_equivalents": item.counted.phd_equivalents,
        "staff_percentage": float(item.staff_percentage),
        "mix": {key: float(getattr(item.mix, key)) for key in item.mix.__slots__},
        "free_seats": item.free_seats,
        "target_shortfall": item.target_shortfall,
        "is_compliant": item.is_compliant,
        "violations": [
            {"kind": str(violation.kind), "message": violation_text(violation)}
            for violation in item.violations
        ],
        "specializations": [
            {
                "name": counted.specialization.name,
                "signed": _counts(item.signed_roster.of(counted.specialization)),
                "counted": _counts(counted),
            }
            for counted in item.counted_roster.counts
        ],
    }


def _counts(item: domain.SpecializationCount) -> dict[str, int]:
    return {
        "fulltime_staff": item.fulltime_staff,
        "fulltime_borrowed": item.fulltime_borrowed,
        "parttime": item.parttime,
        "masters": item.masters,
    }
