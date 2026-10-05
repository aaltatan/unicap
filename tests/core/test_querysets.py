import pytest

from unicap.app.constants import faculty as faculty_constants
from unicap.app.models import Backup, Chapter, Contract, Employee, Faculty, User
from unicap.app.utils import keywords_query, parse_ordering


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", []),
        (None, []),
        ("name", ["name"]),
        ("-name, students ,", ["-name", "students"]),
    ],
)
def test_parse_ordering(value: str | None, expected: list[str]) -> None:
    assert parse_ordering(value) == expected


def test_keywords_query_negates_bang_words() -> None:
    query = keywords_query("dr !sam", ["name"])

    assert "sam" in str(query)
    assert query.children[1].negated


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("dr sa", {"Dr. Sami"}),
        ("Biology", {"Dr. Hala", "Dr. Nour", "Dr. Ziad", "Dr. Maya", "Dr. Rana"}),
        ("dr. !a", {"Dr. Nour"}),  # no "a" in the name, specialization or notes
    ],
)
def test_search_by_keywords(chapter: Chapter, value: str, expected: set[str]) -> None:
    rows = Employee.objects.for_chapter(chapter.pk).search(value)

    assert set(rows.values_list("name", flat=True)) == expected


def test_search_by_djangoql(chapter: Chapter) -> None:
    rows = Faculty.objects.for_chapter(chapter.pk).search("students_per_phd > 12")

    assert set(rows.values_list("name", flat=True)) == {"Pharmacy", "Computer Science"}


def test_order_by_fields_ignores_unknown_fields(chapter: Chapter) -> None:
    rows = Faculty.objects.for_chapter(chapter.pk).order_by_fields(
        ["-students_per_phd", "password"],
        faculty_constants.ORDERING_FIELDS,
    )

    assert list(rows.values_list("name", flat=True)) == [
        "Computer Science",
        "Pharmacy",
        "Dentistry",
    ]


@pytest.mark.parametrize(
    "query",
    [
        'chapter.backups.created_by.username = "admin"',
        'chapter.backups.notes ~ "secret"',
    ],
)
def test_djangoql_never_reaches_users_or_backups(
    chapter: Chapter, admin_user: User, query: str
) -> None:
    Backup.objects.create(scope="chapter", chapter=chapter, created_by=admin_user, notes="secret")

    rows = Faculty.objects.for_chapter(chapter.pk).search(query)

    assert not rows.exists()  # not a DjangoQL query any more: plain keywords, found nowhere


def test_djangoql_still_follows_the_data(chapter: Chapter) -> None:
    rows = Contract.objects.for_chapter(chapter.pk).search('faculty.name = "Pharmacy"')

    assert rows.exists()
    assert set(rows.values_list("faculty__name", flat=True)) == {"Pharmacy"}
