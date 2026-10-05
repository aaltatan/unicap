"""The header's breadcrumb: the page's sidebar section and link, then the page itself."""

import pytest
from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from unicap.app.models import Chapter, Faculty


def crumbs(client: Client, url: str) -> tuple[list[str], list[str], str]:
    """The breadcrumb of `url`: its texts, its links and the page it ends with."""
    nav = HTMLParser(client.get(url).content).css_first("header nav")

    texts = [node.text(strip=True) for node in nav.iter() if node.text(strip=True)]
    links = [a.attributes["href"] for a in nav.css("a")]

    return texts, links, nav.css_first("h1[aria-current='page']").text(strip=True)


@pytest.mark.parametrize(
    ("url_name", "expected"),
    [
        ("board:dashboard", ["overview", "dashboard"]),
        ("hr:contracts:index", ["data", "contracts"]),
        ("reports:audit", ["reports", "calculation audit"]),
        ("chapters:index", ["settings", "chapters"]),
    ],
)
def test_a_sidebar_page_is_under_its_section(
    admin_client: Client,
    chapter: Chapter,
    url_name: str,
    expected: list[str],
) -> None:
    texts, links, page = crumbs(admin_client, reverse(url_name))

    assert texts == expected
    assert links == [reverse("board:dashboard")]  # home; the section is only a label
    assert page == expected[-1]


def test_a_page_below_a_link_can_go_back_up_to_it(admin_client: Client, chapter: Chapter) -> None:
    texts, links, page = crumbs(admin_client, reverse("reports:capacity-pivot"))

    assert texts == ["reports", "capacity report", "capacity pivot"]
    assert links == [reverse("board:dashboard"), reverse("reports:capacity")]
    assert page == "capacity pivot"


def test_a_facultys_report_is_under_the_faculty_reports(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).first()

    texts, links, page = crumbs(admin_client, reverse("reports:staff-pivot", args=(faculty.pk,)))

    assert texts == ["reports", "faculty reports", faculty.name]
    assert links[-1] == reverse("reports:faculties")
    assert page == faculty.name


def test_crumbs_follow_what_the_user_may_see(viewer_client: Client, chapter: Chapter) -> None:
    texts, _links, _page = crumbs(viewer_client, reverse("hr:employees:index"))

    assert texts == ["data", "employees"]
