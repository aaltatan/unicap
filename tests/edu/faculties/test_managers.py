import pytest

from unicap.app.exceptions import UserError
from unicap.app.forms import shares_formset
from unicap.app.models import Chapter, Contract, Employee, Faculty, Specialization
from unicap.domain import DomainError


def _formset_data(faculty: Faculty, rows: list[dict[str, object]]) -> dict[str, object]:
    """POST data for the shares formset: `rows` in order (existing ones carry an `id`)."""
    data: dict[str, object] = {
        "shares-TOTAL_FORMS": len(rows),
        "shares-INITIAL_FORMS": faculty.shares.count(),
        "shares-MIN_NUM_FORMS": 0,
        "shares-MAX_NUM_FORMS": 1000,
    }

    for index, row in enumerate(rows):
        for key, value in row.items():
            data[f"shares-{index}-{key}"] = "" if value is None else value

    return data


def test_attach_reports(chapter: Chapter) -> None:
    faculties = Faculty.objects.attach_reports(Faculty.objects.for_chapter(chapter.pk), chapter.pk)

    capacities = {f.name: f.report.capacity for f in faculties}

    assert capacities == {"Computer Science": 75, "Dentistry": 50, "Pharmacy": 30}
    assert not next(f for f in faculties if f.name == "Dentistry").report.is_compliant


def test_save_with_shares_follows_the_formset_order(chapter: Chapter) -> None:
    faculty = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    [pharmacy_share, biology_share] = faculty.shares.order_by("position")
    medicine = Specialization.objects.get(chapter=chapter, name="Medicine")

    data = _formset_data(
        faculty,
        [
            {
                "id": biology_share.pk,
                "specialization": biology_share.specialization_id,
                "specialization_type": "supported",
                "position": 0,
            },
            {
                "id": pharmacy_share.pk,
                "specialization": pharmacy_share.specialization_id,
                "specialization_type": "specialized",
                "position": 2,
            },
            {"specialization": medicine.pk, "specialization_type": "supported", "position": 1},
        ],
    )

    shares = shares_formset(data, instance=faculty, prefix="shares", chapter=chapter)

    assert shares.is_valid(), shares.errors

    Faculty.objects.save_with_shares(faculty, shares)

    names = list(
        faculty.shares.order_by("position").values_list("specialization__name", flat=True),
    )

    assert names == ["Biology", "Medicine", "Pharmacy"]


def test_save_with_shares_rolls_back_on_a_domain_error(chapter: Chapter) -> None:
    faculty = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    [pharmacy_share, biology_share] = faculty.shares.order_by("position")

    data = _formset_data(
        faculty,
        [
            {
                "id": pharmacy_share.pk,
                "specialization": pharmacy_share.specialization_id,
                "specialization_type": "specialized",
                "percentage": 70,
                "position": 0,
            },
            {
                "id": biology_share.pk,
                "specialization": biology_share.specialization_id,
                "specialization_type": "supported",
                "percentage": 50,
                "position": 1,
            },
        ],
    )

    shares = shares_formset(data, instance=faculty, prefix="shares", chapter=chapter)

    assert shares.is_valid(), shares.errors

    with pytest.raises(DomainError, match="sum to 120%"):
        Faculty.objects.save_with_shares(faculty, shares)

    assert set(faculty.shares.values_list("percentage", flat=True)) == {None}


def test_a_faculty_with_contracts_cannot_be_deleted(chapter: Chapter) -> None:
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    with pytest.raises(UserError, match=r"contracts: Dr\. Fadi, Dr\. Rana"):
        Faculty.objects.delete_many(chapter.pk, [pharmacy.pk])

    assert Faculty.objects.filter(pk=pharmacy.pk).exists()
    assert Contract.objects.filter(faculty=pharmacy).count() == 2


def test_a_faculty_without_contracts_is_deleted(chapter: Chapter) -> None:
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    Contract.objects.filter(faculty=pharmacy).update(faculty=None)

    assert Faculty.objects.delete_many(chapter.pk, [pharmacy.pk])
    assert not Faculty.objects.filter(pk=pharmacy.pk).exists()


def test_an_employee_with_a_contract_cannot_be_deleted(chapter: Chapter) -> None:
    contract = Contract.objects.get(chapter=chapter, employee__name="Dr. Fadi")

    with pytest.raises(UserError, match="contracts"):
        Employee.objects.delete_many(chapter.pk, [contract.employee_id])

    assert Employee.objects.filter(pk=contract.employee_id).exists()

    contract.delete()

    assert Employee.objects.delete_many(chapter.pk, [contract.employee_id])


def test_a_specialization_a_faculty_accepts_cannot_be_deleted(chapter: Chapter) -> None:
    specialization = chapter.specializations.create(name="Astrology")
    faculty = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    faculty.shares.create(specialization=specialization, position=9)

    with pytest.raises(UserError, match="Pharmacy · Astrology"):
        Specialization.objects.delete_many(chapter.pk, [specialization.pk])

    assert Specialization.objects.filter(pk=specialization.pk).exists()


def test_deleting_a_chapter_deletes_everything_it_owns(chapter: Chapter) -> None:
    Chapter.objects.delete_many([chapter.pk])

    assert not Contract.objects.exists()
    assert not Faculty.objects.exists()
    assert not Employee.objects.exists()


def test_the_formset_refuses_a_repeated_specialization(chapter: Chapter) -> None:
    faculty = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    [pharmacy_share, _biology] = faculty.shares.order_by("position")

    data = _formset_data(
        faculty,
        [
            {
                "id": pharmacy_share.pk,
                "specialization": pharmacy_share.specialization_id,
                "specialization_type": "specialized",
                "position": 0,
            },
            {
                "specialization": pharmacy_share.specialization_id,
                "specialization_type": "supported",
                "position": 1,
            },
        ],
    )

    shares = shares_formset(data, instance=faculty, prefix="shares", chapter=chapter)

    assert not shares.is_valid()
