"""`uv run manage.py seed`: a sample chapter to try the app with (pucc's sample university)."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from unicap import domain
from unicap.domain import (
    ChapterFaculty,
    Contract,
    ContractType,
    Degree,
    Employee,
    EmploymentType,
    Faculty,
    Share,
    Specialization,
)

from ...models import Chapter

FULLTIME, PARTTIME = ContractType.FULLTIME, ContractType.PARTTIME
STAFF, BORROWED = EmploymentType.STAFF, EmploymentType.BORROWED


class Command(BaseCommand):
    """`manage.py seed [--name ...]`."""

    help = "Create a sample chapter: specializations, faculties, employees and contracts."

    def add_arguments(self, parser: CommandParser) -> None:  # noqa: D102
        parser.add_argument("--name", default="2026 / Fall", help="the new chapter's name")

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Save the sample chapter through `Chapter.objects.create_from_domain`."""
        name = options["name"]

        if Chapter.objects.filter(name=name).exists():
            msg = f"A chapter named {name!r} exists already: pass another --name."
            raise CommandError(msg)

        chapter = Chapter.objects.create_from_domain(
            sample_chapter(name),
            notes="Sample data: try the board, the optimizer and the tables.",
        )

        self.stdout.write(self.style.SUCCESS(f"Created {chapter.name} (id {chapter.pk})."))


def sample_chapter(name: str) -> domain.Chapter:
    """Six specializations, three faculties (old and new methods) and sixteen teachers."""
    dentistry, biology, medicine, pharmacy, computing, mathematics = (
        Specialization(s)
        for s in (
            "Dentistry",
            "Biology",
            "Medicine",
            "Pharmacy",
            "Computer Science",
            "Mathematics",
        )
    )

    faculties = {
        "Dentistry": ChapterFaculty(
            Faculty("Dentistry", specialized=(dentistry,), supported=(biology, medicine)),
            students_per_phd=10,
            current_students=40,
            target_students=60,
            max_students=80,
            shares=(
                Share(dentistry, percentage=60, min_percentage=50, max_percentage=70),
                Share(biology, percentage=20, min_percentage=10, max_percentage=30),
                Share(medicine, percentage=20, min_percentage=10, max_percentage=30),
            ),
        ),
        "Pharmacy": ChapterFaculty(
            Faculty("Pharmacy", specialized=(pharmacy,), supported=(biology,)),
            students_per_phd=15,
            current_students=20,
            target_students=90,
            max_students=120,
        ),
        "Computer Science": ChapterFaculty(
            Faculty("Computer Science", specialized=(computing,), supported=(mathematics,)),
            students_per_phd=25,
            current_students=60,
            target_students=150,
            max_students=200,
        ),
    }

    specializations = {
        s.name: s for s in (dentistry, biology, medicine, pharmacy, computing, mathematics)
    }

    teachers = [
        ("Dr. Sami", "Dentistry", Degree.PHD, FULLTIME, STAFF, "Dentistry"),
        ("Dr. Lina", "Dentistry", Degree.PHD, FULLTIME, STAFF, "Dentistry"),
        ("Dr. Omar", "Dentistry", Degree.PHD, FULLTIME, BORROWED, "Dentistry"),
        ("Dr. Hala", "Biology", Degree.PHD, FULLTIME, STAFF, "Dentistry"),
        ("Dr. Rami", "Medicine", Degree.PHD, FULLTIME, BORROWED, "Dentistry"),
        ("Dr. Nour", "Biology", Degree.PHD, PARTTIME, BORROWED, "Dentistry"),
        ("Dr. Ziad", "Biology", Degree.PHD, PARTTIME, BORROWED, "Dentistry"),
        ("Dr. Maya", "Biology", Degree.PHD, PARTTIME, BORROWED, "Dentistry"),
        ("Dr. Fadi", "Pharmacy", Degree.PHD, FULLTIME, STAFF, "Pharmacy"),
        ("Dr. Rana", "Biology", Degree.PHD, FULLTIME, STAFF, "Pharmacy"),
        ("Dr. Karim", "Pharmacy", Degree.PHD, PARTTIME, BORROWED, None),
        ("Dr. Adel", "Computer Science", Degree.PHD, FULLTIME, STAFF, "Computer Science"),
        ("Dr. Dana", "Mathematics", Degree.PHD, FULLTIME, STAFF, "Computer Science"),
        ("Dr. Elias", "Computer Science", Degree.PHD, PARTTIME, BORROWED, "Computer Science"),
        ("Nabil", "Computer Science", Degree.MASTER, FULLTIME, STAFF, "Computer Science"),
        ("Ola", "Computer Science", Degree.MASTER, FULLTIME, STAFF, None),
    ]

    contracts = [
        Contract(
            Employee(number, teacher, specializations[specialization]),
            contract_type,
            employment_type,
            faculties[faculty].faculty if faculty else None,
            degree=degree,
        )
        for number, (
            teacher,
            specialization,
            degree,
            contract_type,
            employment_type,
            faculty,
        ) in enumerate(teachers, start=1)
    ]

    return domain.Chapter.assemble(
        name,
        contracts,
        faculties=tuple(faculties.values()),
        specializations=tuple(specializations.values()),
    )
