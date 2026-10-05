"""Violations shown as sentences in the user's language, from the domain's params."""

from fractions import Fraction

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation

from unicap.app.models import Chapter, Faculty
from unicap.app.templatetags.domain import violation_text
from unicap.domain import SpecializationType, Violation, ViolationKind

STAFF = Violation(
    ViolationKind.STAFF_RATIO_TOO_LOW,
    "Dentistry: staff are 40.0% of PhDs, minimum is 50%",
    {"faculty": "Dentistry", "percentage": Fraction(2, 5) * 100, "minimum": 50},
)

TYPE = Violation(
    ViolationKind.TOO_FEW_OF_TYPE,
    "Dentistry: 1 counted supported PhD(s), minimum is 2",
    {"faculty": "Dentistry", "type": SpecializationType.SUPPORTED, "counted": 1, "minimum": 2},
)


@pytest.mark.parametrize("violation", [STAFF, TYPE])
def test_in_english_the_sentence_is_the_domains(violation: Violation) -> None:
    with translation.override("en"):
        assert violation_text(violation) == violation.message


def test_in_arabic_the_sentence_is_translated_with_its_values() -> None:
    with translation.override("ar"):
        text = violation_text(STAFF)

    assert text.startswith("Dentistry: ")
    assert "40.0%" in text
    assert "50%" in text
    assert "staff" not in text


def test_the_type_is_labelled_in_the_language() -> None:
    with translation.override("ar"):
        text = violation_text(TYPE)
        supported = translation.gettext("supported")

    assert supported in text


def test_a_violation_without_params_keeps_its_message() -> None:
    violation = Violation(ViolationKind.TOO_FEW_TEACHERS, "some rule is broken")

    with translation.override("ar"):
        assert violation_text(violation) == "some rule is broken"


def test_the_arabic_board_shows_translated_issues(admin_client: Client, chapter: Chapter) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).first()
    Faculty.objects.filter(pk=faculty.pk).update(min_staff_percentage=100)

    response = admin_client.get(reverse("board:index"), HTTP_ACCEPT_LANGUAGE="ar")

    content = response.content.decode()

    assert f"{faculty.name}: نسبة الملاك" in content  # "staff are ..." in Arabic
    assert "staff are" not in content
