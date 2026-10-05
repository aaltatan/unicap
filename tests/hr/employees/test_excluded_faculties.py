"""An employee's excluded faculties, from the form to the domain and back."""

import csv
import io
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from tests.factories import FacultyFactory
from unicap.app.backups import payload
from unicap.app.models import Chapter, Contract, Employee, Faculty
from unicap.domain import ContractStatus


def signed(chapter: Chapter) -> Contract:
    """A counted contract of the sample chapter."""
    contracts = Contract.objects.attach_statuses(
        Contract.objects.for_chapter(chapter.pk).signed().with_relations(), chapter.pk
    )

    return next(c for c in contracts if c.status is ContractStatus.COUNTED)


def exclude(employee: Employee, *faculties: Faculty) -> None:
    employee.excluded_faculties.set(faculties)


def status_of(contract: Contract) -> ContractStatus | None:
    [row] = Contract.objects.attach_statuses([contract], contract.chapter_id)

    return row.status


# --- the domain reads the rows ------------------------------------------------------------


def test_the_domain_employee_holds_the_excluded_faculties_names(chapter: Chapter) -> None:
    contract = signed(chapter)
    exclude(contract.employee, contract.faculty)

    snapshot = Chapter.objects.get_snapshot(chapter.pk)

    assert snapshot.employees[contract.employee_id].excluded_faculties == {contract.faculty.name}


def test_a_contract_signed_to_an_excluded_faculty_is_not_counted(chapter: Chapter) -> None:
    contract = signed(chapter)
    before = Chapter.objects.get_snapshot(chapter.pk).report().capacity

    exclude(contract.employee, contract.faculty)

    assert status_of(contract) is ContractStatus.FACULTY_NOT_ALLOWED
    assert Chapter.objects.get_snapshot(chapter.pk).report().capacity <= before


def test_excluded_from_another_faculty_keeps_the_contract_counted(chapter: Chapter) -> None:
    contract = signed(chapter)
    other = Faculty.objects.for_chapter(chapter.pk).exclude(pk=contract.faculty_id).first()

    exclude(contract.employee, other)

    assert status_of(contract) is ContractStatus.COUNTED


def test_reading_a_chapter_does_not_query_each_employee(
    chapter: Chapter,
    django_assert_max_num_queries: object,
) -> None:
    for employee in chapter.employees.all()[:5]:
        exclude(employee, chapter.faculties.first())

    with django_assert_max_num_queries(12):  # type: ignore[operator]
        Chapter.objects.get_snapshot(chapter.pk)


# --- the form -----------------------------------------------------------------------------


def test_the_form_offers_the_chapters_faculties_only(
    admin_client: Client, chapter: Chapter
) -> None:
    FacultyFactory(name="Elsewhere")  # of another chapter
    employee = chapter.employees.first()

    response = admin_client.get(reverse("hr:employees:update", args=(employee.pk,)), **htmx())

    offered = {
        box.attributes["value"]
        for box in HTMLParser(response.content).css('input[name="excluded_faculties"]')
    }

    assert offered == {str(pk) for pk in chapter.faculties.values_list("pk", flat=True)}


def test_saving_the_form_saves_the_excluded_faculties(
    admin_client: Client, chapter: Chapter
) -> None:
    contract = signed(chapter)
    employee = contract.employee

    response = admin_client.post(
        reverse("hr:employees:update", args=(employee.pk,)),
        {
            "name": employee.name,
            "specialization": employee.specialization_id,
            "is_active": "on",
            "excluded_faculties": [contract.faculty_id],
        },
        **htmx(),
    )

    assert json.loads(response["HX-Trigger"])["refresh"] is True
    assert list(employee.excluded_faculties.all()) == [contract.faculty]
    assert status_of(contract) is ContractStatus.FACULTY_NOT_ALLOWED


def test_a_new_employee_is_saved_with_them(admin_client: Client, chapter: Chapter) -> None:
    faculty = chapter.faculties.first()

    admin_client.post(
        reverse("hr:employees:create"),
        {
            "name": "Dr. New",
            "specialization": chapter.specializations.first().pk,
            "is_active": "on",
            "excluded_faculties": [faculty.pk],
        },
        **htmx(),
    )

    assert list(chapter.employees.get(name="Dr. New").excluded_faculties.all()) == [faculty]


def test_the_modal_lists_where_the_employee_cannot_be_counted(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    contract = signed(chapter)
    exclude(contract.employee, contract.faculty)

    details = admin_client.get(contract.employee.get_absolute_url(), **htmx())
    table = admin_client.get(reverse("hr:contracts:index"), {"q": contract.employee.name})

    assert "cannot be counted in" in details.content.decode()
    assert contract.faculty.name in HTMLParser(details.content).css_first("dl").text()
    assert "the employee cannot be counted in this faculty" in table.content.decode()


# --- copies, files, backups ---------------------------------------------------------------


def test_a_duplicate_keeps_them_pointing_at_its_own_faculties(chapter: Chapter) -> None:
    contract = signed(chapter)
    exclude(contract.employee, contract.faculty)

    copy = Chapter.objects.duplicate(chapter, "Copy")

    [excluded] = copy.employees.get(name=contract.employee.name).excluded_faculties.all()

    assert excluded.chapter == copy
    assert excluded.name == contract.faculty.name
    assert list(contract.employee.excluded_faculties.all()) == [contract.faculty]  # untouched


def test_a_chapter_made_from_the_domain_keeps_them(chapter: Chapter) -> None:
    contract = signed(chapter)
    exclude(contract.employee, contract.faculty)

    value = Chapter.objects.get_domain(chapter.pk)
    chapter.delete()

    restored = Chapter.objects.create_from_domain(value)

    employee = restored.employees.get(name=contract.employee.name)
    assert [f.name for f in employee.excluded_faculties.all()] == [contract.faculty.name]


def test_export_and_import_write_them_as_a_list_of_names(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    first, second, *_rest = chapter.faculties.order_by("name")
    employee = chapter.employees.order_by("name").first()
    exclude(employee, first, second)

    response = admin_client.get(
        reverse("hr:employees:index"), {"export": "csv", "q": employee.name}
    )
    [headers, row] = csv.reader(io.StringIO(response.content.decode("utf-8-sig")))
    column = headers.index("cannot be counted in")

    assert row[column] == f"{first.name}; {second.name}"

    row[column] = second.name
    output = io.StringIO()
    csv.writer(output).writerows([headers, row])
    upload = SimpleUploadedFile("employees.csv", output.getvalue().encode("utf-8-sig"))

    admin_client.post(reverse("hr:employees:import"), {"file": upload}, **htmx())

    assert list(employee.excluded_faculties.all()) == [second]


def test_an_import_refuses_a_faculty_that_is_not_the_chapters(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    content = "name,specialization,excluded_faculties\nDr. New,Biology,Astrology\n"
    upload = SimpleUploadedFile("employees.csv", content.encode())

    response = admin_client.post(reverse("hr:employees:import"), {"file": upload}, **htmx())

    assert "Astrology" in response.content.decode()
    assert not chapter.employees.filter(name="Dr. New").exists()


def test_a_backup_holds_and_restores_them(chapter: Chapter) -> None:
    contract = signed(chapter)
    employee = contract.employee
    exclude(employee, contract.faculty)

    data = payload.dump_chapter(chapter, ["employees"])
    row = next(item for item in data["employees"] if item["name"] == employee.name)

    assert row["excluded_faculties"] == [contract.faculty.name]

    exclude(employee)
    payload.load_chapter(chapter, data, settings=False)

    assert list(employee.excluded_faculties.all()) == [contract.faculty]


def test_a_backup_made_before_the_constraint_still_restores(chapter: Chapter) -> None:
    data = payload.dump_chapter(chapter, ["employees"])

    for row in data["employees"]:
        del row["excluded_faculties"]

    payload.load_chapter(chapter, data, settings=False)

    assert not Employee.objects.filter(chapter=chapter, excluded_faculties__isnull=False).exists()
