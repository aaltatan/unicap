"""factory-boy factories for every model: one chapter's rows by default."""

import factory
from factory.django import DjangoModelFactory

from unicap.app.choices import (
    ContractTypeChoices,
    DegreeChoices,
    EmploymentTypeChoices,
    SpecializationTypeChoices,
)
from unicap.app.models import (
    Chapter,
    Contract,
    Employee,
    Faculty,
    FacultySpecialization,
    Specialization,
)


class ChapterFactory(DjangoModelFactory):
    class Meta:
        model = Chapter

    name = factory.Sequence(lambda n: f"Chapter {n}")


class SpecializationFactory(DjangoModelFactory):
    class Meta:
        model = Specialization

    chapter = factory.SubFactory(ChapterFactory)
    name = factory.Sequence(lambda n: f"Specialization {n}")


class FacultyFactory(DjangoModelFactory):
    class Meta:
        model = Faculty

    chapter = factory.SubFactory(ChapterFactory)
    name = factory.Sequence(lambda n: f"Faculty {n}")
    students_per_phd = 10


class FacultySpecializationFactory(DjangoModelFactory):
    class Meta:
        model = FacultySpecialization

    faculty = factory.SubFactory(FacultyFactory)
    specialization = factory.SubFactory(
        SpecializationFactory,
        chapter=factory.SelfAttribute("..faculty.chapter"),
    )
    specialization_type = SpecializationTypeChoices.SPECIALIZED


class EmployeeFactory(DjangoModelFactory):
    class Meta:
        model = Employee

    chapter = factory.SubFactory(ChapterFactory)
    name = factory.Sequence(lambda n: f"Dr. {n}")
    specialization = factory.SubFactory(
        SpecializationFactory,
        chapter=factory.SelfAttribute("..chapter"),
    )


class ContractFactory(DjangoModelFactory):
    class Meta:
        model = Contract

    employee = factory.SubFactory(EmployeeFactory)
    chapter = factory.SelfAttribute("employee.chapter")
    contract_type = ContractTypeChoices.FULLTIME
    employment_type = EmploymentTypeChoices.STAFF
    degree = DegreeChoices.PHD
    position = factory.Sequence(lambda n: n)
