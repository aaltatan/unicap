import pytest

from tests.factories import ContractFactory, EmployeeFactory, FacultyFactory
from unicap.app.models import Chapter, Contract, Employee, Faculty
from unicap.domain import ContractStatus, DomainError


def test_move_signs_the_contract_last(chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    Contract.objects.move(karim, pharmacy.pk)

    karim.refresh_from_db()
    assert karim.faculty == pharmacy
    assert (
        karim.position
        == Contract.objects.for_chapter(chapter.pk).order_by("position").last().position
    )


def test_move_to_another_chapters_faculty_is_refused(chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")
    elsewhere = FacultyFactory()

    with pytest.raises(DomainError, match="not in this chapter"):
        Contract.objects.move(karim, elsewhere.pk)

    karim.refresh_from_db()
    assert karim.faculty is None


def test_save_contract_takes_the_employees_chapter(chapter: Chapter) -> None:
    employee = EmployeeFactory(chapter=chapter, specialization=chapter.specializations.first())

    contract = Contract.objects.save_contract(Contract(employee=employee))

    assert contract.chapter == chapter


def test_attach_statuses(chapter: Chapter) -> None:
    rows = Contract.objects.attach_statuses(
        Contract.objects.for_chapter(chapter.pk).with_relations(),
        chapter.pk,
    )

    statuses = {row.employee.name: row.status for row in rows}

    assert statuses["Dr. Sami"] is ContractStatus.COUNTED
    assert statuses["Dr. Karim"] is None  # unsigned
    assert statuses["Dr. Nour"] is ContractStatus.SHARE_OVERFLOW


def test_toggle_contract(chapter: Chapter) -> None:
    sami = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")

    Contract.objects.toggle_active(sami)

    [row] = Contract.objects.attach_statuses([sami], chapter.pk)
    assert row.status is ContractStatus.INACTIVE


def test_employee_statuses_follow_their_contract(chapter: Chapter) -> None:
    rows = Employee.objects.attach_statuses(Employee.objects.for_chapter(chapter.pk), chapter.pk)

    assert {r.name: r.status for r in rows}["Dr. Elias"] is ContractStatus.COUNTED


@pytest.mark.django_db
def test_signed_and_unsigned() -> None:
    signed = ContractFactory(faculty=FacultyFactory())
    unsigned = ContractFactory()

    assert list(Contract.objects.signed()) == [signed]
    assert list(Contract.objects.unsigned()) == [unsigned]
