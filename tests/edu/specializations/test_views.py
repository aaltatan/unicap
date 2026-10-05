"""The specialization's modal: every teacher holding it, on one line each."""

from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from tests.factories import EmployeeFactory
from unicap.app.models import Chapter, Employee, Specialization
from unicap.app.templatetags.domain import status_label


def lines(client: Client, specialization: Specialization) -> dict[str, list[str]]:
    """Each teacher's line in the modal, split at its dots, by the teacher's name."""
    url = reverse("edu:specializations:details", args=(specialization.pk,))
    tree = HTMLParser(client.get(url, **htmx()).content)

    rows = [[part.strip() for part in item.text().split("·")] for item in tree.css("ul li")]

    return {name: rest for name, *rest in rows}


def test_each_teacher_is_a_line_of_name_then_everything_about_them(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    specialization = Specialization.objects.filter(
        chapter=chapter, employees__contract__faculty__isnull=False
    ).first()

    employees = Employee.objects.attach_statuses(
        Employee.objects.for_chapter(chapter.pk)
        .holding(specialization.pk)
        .with_contract()
        .annotate_specialization_type(),
        chapter.pk,
    )

    found = lines(admin_client, specialization)

    assert set(found) == {employee.name for employee in employees}

    for employee in employees:
        contract = employee.contract
        expected = [
            contract.faculty.name if contract.faculty else "unsigned",
            *([employee.specialization_type] if employee.specialization_type else []),
            contract.get_degree_display(),
            f"{contract.get_contract_type_display()} {contract.get_employment_type_display()}",
            status_label(employee.status),
        ]

        assert found[employee.name][: len(expected)] == expected


def test_a_teacher_without_a_contract_says_so(admin_client: Client, chapter: Chapter) -> None:
    specialization = Specialization.objects.filter(chapter=chapter).first()
    EmployeeFactory(chapter=chapter, specialization=specialization, name="Dr. New")

    assert lines(admin_client, specialization)["Dr. New"] == ["no contract"]


def test_a_teachers_name_opens_their_modal(admin_client: Client, chapter: Chapter) -> None:
    specialization = Specialization.objects.filter(chapter=chapter, employees__isnull=False).first()
    employee = specialization.employees.first()

    url = reverse("edu:specializations:details", args=(specialization.pk,))
    tree = HTMLParser(admin_client.get(url, **htmx()).content)

    assert tree.css_first(f'li button[hx-get="{employee.get_absolute_url()}"]') is not None
