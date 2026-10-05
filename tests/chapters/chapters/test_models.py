"""`to_domain` / `from_domain` on every model: rows <-> the domain's values."""

import pytest

from tests.factories import (
    ContractFactory,
    EmployeeFactory,
    FacultyFactory,
    FacultySpecializationFactory,
    SpecializationFactory,
)
from unicap import domain
from unicap.app.choices import SpecializationTypeChoices
from unicap.app.models import (
    Chapter,
    Contract,
    Employee,
    Faculty,
    FacultySpecialization,
    Specialization,
)


@pytest.mark.django_db
def test_specialization_round_trip() -> None:
    row = SpecializationFactory(name="Biology", is_active=False)

    value = row.to_domain()

    assert value == domain.Specialization("Biology")
    assert value.is_active is False

    copy = Specialization.from_domain(value, chapter_id=row.chapter_id)

    assert (copy.pk, copy.name, copy.is_active, copy.chapter_id) == (
        None,
        "Biology",
        False,
        row.chapter_id,
    )


@pytest.mark.django_db
def test_faculty_to_domain_keeps_types_order_and_shares() -> None:
    faculty = FacultyFactory(name="Dentistry", students_per_phd=12, max_students=80)
    biology = FacultySpecializationFactory(
        faculty=faculty,
        specialization__name="Biology",
        specialization_type=SpecializationTypeChoices.SUPPORTED,
        percentage=40,
        position=1,
    )
    dentistry = FacultySpecializationFactory(
        faculty=faculty,
        specialization__name="Dentistry",
        percentage=60,
        min_teachers=2,
        position=0,
    )

    value = faculty.to_domain()

    assert isinstance(value, domain.ChapterFaculty)
    assert value.faculty.specialized == (dentistry.specialization.to_domain(),)
    assert value.faculty.supported == (biology.specialization.to_domain(),)
    assert [share.percentage for share in value.shares] == [60, 40]
    assert value.share_of(domain.Specialization("Dentistry")).min_teachers == 2
    assert (value.students_per_phd, value.max_students) == (12, 80)


@pytest.mark.django_db
def test_faculty_from_domain_copies_the_numbers() -> None:
    value = domain.ChapterFaculty(
        domain.Faculty("Pharmacy"),
        students_per_phd=15,
        min_staff_percentage=60,
        target_students=90,
        max_supported=3,
    )

    faculty = Faculty.from_domain(value, chapter_id=None)

    assert faculty.name == "Pharmacy"
    assert faculty.students_per_phd == 15
    assert faculty.min_staff_percentage == 60
    assert faculty.target_students == 90
    assert faculty.max_supported == 3


@pytest.mark.django_db
def test_share_from_domain() -> None:
    share = domain.Share(domain.Specialization("Biology"), percentage=20, max_percentage=30)

    row = FacultySpecialization.from_domain(
        share,
        faculty_id=1,
        specialization_id=2,
        specialization_type=domain.SpecializationType.SUPPORTED,
        position=3,
    )

    assert (row.faculty_id, row.specialization_id, row.position) == (1, 2, 3)
    assert row.specialization_type == "supported"
    assert (row.percentage, row.min_percentage, row.max_percentage) == (20, None, 30)


@pytest.mark.django_db
def test_employee_round_trip_uses_the_row_id() -> None:
    row = EmployeeFactory(name="Dr. Sami", specialization__name="Dentistry")

    value = row.to_domain()

    assert value == domain.Employee(row.pk, "Dr. Sami", domain.Specialization("Dentistry"))

    copy = Employee.from_domain(value, chapter_id=row.chapter_id, specialization_id=9)

    assert (copy.name, copy.specialization_id) == ("Dr. Sami", 9)


@pytest.mark.django_db
def test_contract_round_trip() -> None:
    faculty = FacultyFactory(name="Dentistry")
    row = ContractFactory(
        employee__chapter=faculty.chapter,
        faculty=faculty,
        contract_type="parttime",
        employment_type="borrowed",
        degree="master",
        is_active=False,
    )

    value = row.to_domain()

    assert value.contract_type is domain.ContractType.PARTTIME
    assert value.employment_type is domain.EmploymentType.BORROWED
    assert value.degree is domain.Degree.MASTER
    assert value.faculty is not None
    assert value.faculty.name == "Dentistry"
    assert value.is_active is False

    copy = Contract.from_domain(value, chapter_id=faculty.chapter_id, faculty_id=faculty.pk)

    assert copy.employee_id == row.employee_id
    assert (copy.contract_type, copy.employment_type, copy.degree) == (
        "parttime",
        "borrowed",
        "master",
    )


@pytest.mark.django_db
def test_parttime_staff_contract_is_refused_by_the_domain() -> None:
    row = ContractFactory.build(
        employee=EmployeeFactory(),
        contract_type="parttime",
        employment_type="staff",
    )

    with pytest.raises(domain.DomainError, match="always borrowed"):
        row.to_domain()


def test_chapter_to_domain_is_the_whole_aggregate(chapter: Chapter) -> None:
    value = Chapter.objects.with_domain_relations().get(pk=chapter.pk).to_domain()

    assert value.name == "2026 / Fall"
    assert len(value.specializations) == 6
    assert [f.name for f in value.faculties] == ["Computer Science", "Dentistry", "Pharmacy"]
    assert len(value.employees) == len(value.contracts) == 16
    assert [c.employee.name for c in value.contracts][:3] == ["Dr. Sami", "Dr. Lina", "Dr. Omar"]
    assert len(value.unsigned) == 2


def test_chapter_from_domain() -> None:
    chapter = Chapter.from_domain(domain.Chapter("2027 / Spring", max_students=None))

    assert (chapter.name, chapter.max_students) == ("2027 / Spring", None)


def test_a_share_row_round_trips_its_masters_and_contract_type(chapter: Chapter) -> None:
    share = FacultySpecialization.objects.filter(faculty__chapter=chapter).first()
    share.contract_type = "parttime"
    share.calculate_masters = False
    share.masters_per_phd = 3
    share.save()

    value = share.to_domain()

    assert (value.contract_type, value.calculate_masters, value.masters_per_phd) == (
        domain.ContractType.PARTTIME,
        False,
        3,
    )
    copy = FacultySpecialization.from_domain(value)
    assert (copy.contract_type, copy.calculate_masters, copy.masters_per_phd) == (
        "parttime",
        False,
        3,
    )


def test_create_from_domain_round_trips(chapter: Chapter) -> None:
    value = Chapter.objects.get_domain(chapter.pk)

    copy = Chapter.objects.create_from_domain(
        domain.Chapter.assemble(
            "copy",
            value.contracts,
            faculties=value.faculties,
            specializations=value.specializations,
        ),
    )

    again = Chapter.objects.get_domain(copy.pk)

    assert domain.evaluate_chapter(again).capacity == domain.evaluate_chapter(value).capacity
    assert [c.faculty for c in again.contracts] == [c.faculty for c in value.contracts]
