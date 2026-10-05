"""How many SQL queries each page runs: a ceiling per page, and none grows with its rows.

The ceilings are the counts measured with `scripts/profile_queries.py` (and django-silk) plus
a little room; a page that goes over has gained a query per row or a repeated one.
"""

from collections.abc import Callable

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tests.conftest import htmx
from tests.factories import ContractFactory, EmployeeFactory
from unicap.app.models import Chapter, Contract, Employee, Faculty, Specialization

Url = Callable[[Chapter], str]


def first(model: type, chapter: Chapter, url: str) -> str:
    return getattr(model.objects.filter(chapter=chapter).first(), url)()


def staff_report(chapter: Chapter) -> str:
    faculty = Faculty.objects.filter(chapter=chapter, contracts__isnull=False).first()

    return reverse("reports:staff", args=(faculty.pk,))


PAGES: list[tuple[str, Url, int, bool]] = [
    # name, url, most queries, as an HTMX request
    ("dashboard", lambda _: reverse("board:dashboard"), 13, False),
    ("board", lambda _: reverse("board:index"), 13, False),
    ("contracts table", lambda _: reverse("hr:contracts:index"), 17, False),
    ("employees table", lambda _: reverse("hr:employees:index"), 17, False),
    ("faculties table", lambda _: reverse("edu:faculties:index"), 17, False),
    ("specializations table", lambda _: reverse("edu:specializations:index"), 8, False),
    ("chapters table", lambda _: reverse("chapters:index"), 8, False),
    ("contract modal", lambda c: first(Contract, c, "get_absolute_url"), 13, True),
    ("contract form", lambda c: first(Contract, c, "get_update_url"), 9, True),
    ("employee modal", lambda c: first(Employee, c, "get_absolute_url"), 14, True),
    ("employee form", lambda c: first(Employee, c, "get_update_url"), 9, True),
    ("faculty modal", lambda c: first(Faculty, c, "get_absolute_url"), 14, True),
    ("faculty form", lambda c: first(Faculty, c, "get_update_url"), 8, True),
    ("specialization modal", lambda c: first(Specialization, c, "get_absolute_url"), 15, True),
    ("capacity report", lambda _: reverse("reports:capacity"), 13, False),
    ("capacity pivot", lambda _: reverse("reports:capacity-pivot"), 13, False),
    ("calculation audit", lambda _: reverse("reports:audit"), 13, False),
    ("faculty reports", lambda _: reverse("reports:faculties"), 14, False),
    ("staff report", staff_report, 15, False),
    ("capacity docx", lambda _: reverse("reports:capacity-docx"), 13, False),
    ("employees export", lambda _: reverse("hr:employees:index") + "?export=csv", 14, False),
    ("contracts export", lambda _: reverse("hr:contracts:index") + "?export=csv", 6, False),
]


def queries(client: Client, url: str, *, as_htmx: bool = False) -> int:
    """The queries of one request (a first one warms the caches up: settings, content types)."""
    headers = htmx() if as_htmx else {}

    _drain(client.get(url, **headers))

    with CaptureQueriesContext(connection) as captured:
        response = client.get(url, **headers)
        _drain(response)

    assert response.status_code == 200

    return len(captured)


def _drain(response: object) -> None:
    if hasattr(response, "streaming_content"):
        b"".join(response.streaming_content)


def grow(chapter: Chapter, employees: int) -> None:
    """More employees in the chapter, each with a signed contract and an excluded faculty."""
    specialization = chapter.specializations.first()
    signed_to, excluded = chapter.faculties.all()[:2]

    for number in range(employees):
        employee = EmployeeFactory(
            chapter=chapter, specialization=specialization, name=f"Dr. Extra {number:03}"
        )
        employee.excluded_faculties.add(excluded)
        ContractFactory(chapter=chapter, employee=employee, faculty=signed_to)


@pytest.mark.parametrize(
    ("url", "most", "as_htmx"),
    [pytest.param(url, most, as_htmx, id=name) for name, url, most, as_htmx in PAGES],
)
def test_a_page_stays_within_its_queries(
    admin_client: Client,
    chapter: Chapter,
    url: Url,
    most: int,
    as_htmx: bool,  # noqa: FBT001
) -> None:
    assert queries(admin_client, url(chapter), as_htmx=as_htmx) <= most


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(url, id=name)
        for name, url, _most, as_htmx in PAGES
        if not as_htmx and name != "chapters table"
    ],
)
def test_a_page_runs_the_same_queries_whatever_its_rows(
    admin_client: Client,
    chapter: Chapter,
    url: Url,
) -> None:
    separator = "&" if "?" in url(chapter) else "?"
    page = f"{url(chapter)}{separator}per_page=100"

    before = queries(admin_client, page)

    grow(chapter, 60)

    assert queries(admin_client, page) == before


def test_the_chapters_table_does_not_grow_with_what_chapters_hold(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    url = reverse("chapters:index")
    before = queries(admin_client, url)

    grow(chapter, 60)
    Chapter.objects.duplicate(chapter, "Copy")

    assert queries(admin_client, url) == before


def test_chapter_counts_are_exact_with_many_rows(chapter: Chapter) -> None:
    grow(chapter, 5)

    row = Chapter.objects.annotate_counts().get(pk=chapter.pk)

    assert row.faculties_count == chapter.faculties.count()
    assert row.employees_count == chapter.employees.count()
    assert row.contracts_count == chapter.contracts.count()
    assert row.signed_count == chapter.contracts.filter(faculty__isnull=False).count()


def test_faculty_counts_are_exact(chapter: Chapter) -> None:
    for row in Faculty.objects.for_chapter(chapter.pk).annotate_counts():
        shares = row.shares.all()

        assert row.contracts_count == row.contracts.count()
        assert row.specialized_count == shares.filter(specialization_type="specialized").count()
        assert row.supported_count == shares.filter(specialization_type="supported").count()
