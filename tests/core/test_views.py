"""Every page: logins, permissions, whole pages vs HTMX partials, and the HTMX headers."""

import json
from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.models import Chapter, Contract, Faculty, Specialization, User

INDEX_PAGES = [
    "board:dashboard",
    "board:index",
    "reports:capacity",
    "chapters:index",
    "edu:specializations:index",
    "edu:faculties:index",
    "hr:employees:index",
    "hr:contracts:index",
]

TABLES = [
    "chapters:index",
    "edu:specializations:index",
    "edu:faculties:index",
    "hr:employees:index",
    "hr:contracts:index",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", INDEX_PAGES)
def test_pages_need_a_login(client: Client, url_name: str) -> None:
    response = client.get(reverse(url_name))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


@pytest.mark.parametrize("url_name", INDEX_PAGES)
def test_pages_render(admin_client: Client, chapter: Chapter, url_name: str) -> None:
    response = admin_client.get(reverse(url_name))

    assert response.status_code == 200

    html = HTMLParser(response.content)
    assert html.css_first("nav[aria-label]") is not None  # the sidebar
    assert html.css_first("#modal-container") is not None


@pytest.mark.parametrize("url_name", TABLES)
def test_tables_have_the_filters_sidebar(
    admin_client: Client, chapter: Chapter, url_name: str
) -> None:
    html = HTMLParser(admin_client.get(reverse(url_name)).content)

    assert html.css_first("aside form#filters-form") is not None
    assert html.css_first("#table table") is not None


@pytest.mark.parametrize("url_name", TABLES)
def test_htmx_gets_only_the_table(admin_client: Client, chapter: Chapter, url_name: str) -> None:
    response = admin_client.get(reverse(url_name), **htmx("table"))

    assert response.status_code == 200

    html = HTMLParser(response.content)
    assert html.css_first("table") is not None
    assert html.css_first("nav[aria-label]") is None


def test_rtl_in_arabic(admin_client: Client, chapter: Chapter) -> None:
    admin_client.post(reverse("set_language"), {"language": "ar", "next": "/"})

    html = HTMLParser(admin_client.get(reverse("board:dashboard")).content)

    assert html.css_first("html").attributes["dir"] == "rtl"
    assert html.css_first("html").attributes["lang"] == "ar"


def test_search_and_filters(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(
        reverse("hr:contracts:index"),
        {"q": "dr", "contract_type": "parttime"},
        **htmx("table"),
    )

    names = {
        n.text(strip=True) for n in HTMLParser(response.content).css("td[data-col=employee] button")
    }

    assert names == {"Dr. Nour", "Dr. Ziad", "Dr. Maya", "Dr. Karim", "Dr. Elias"}


def test_sorting_marks_the_column(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(
        reverse("edu:faculties:index"),
        {"ordering": "-students_per_phd"},
        **htmx("table"),
    )

    html = HTMLParser(response.content)
    names = [n.text(strip=True) for n in html.css("td[data-col=name] button")]

    assert names == ["Computer Science", "Pharmacy", "Dentistry"]


def test_viewers_cannot_write(viewer_client: Client, chapter: Chapter) -> None:
    assert viewer_client.get(reverse("hr:contracts:index")).status_code == 200
    assert viewer_client.get(reverse("hr:contracts:create")).status_code == 403
    assert viewer_client.post(reverse("board:move"), {"employee": 1}).status_code == 403


def test_viewers_see_no_write_buttons(viewer_client: Client, chapter: Chapter) -> None:
    html = HTMLParser(viewer_client.get(reverse("hr:contracts:index")).content)

    assert html.css_first(f"[hx-get='{reverse('hr:contracts:create')}']") is None
    assert html.css_first("input[name=ids]") is None


def test_create_closes_the_modal_and_refreshes(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.post(
        reverse("edu:specializations:create"),
        {"name": "History", "is_active": "on"},
        **htmx(),
    )

    assert response.status_code == 200
    assert json.loads(response["HX-Trigger"]) == {"close-modal": True, "refresh": True}
    assert b"hx-swap-oob" in response.content  # the "created" toast
    assert Specialization.objects.filter(chapter=chapter, name="History").exists()


def test_save_and_new_reopens_the_form(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.post(
        reverse("edu:specializations:create"),
        {"name": "History", "save_and_new": "1"},
        **htmx(),
    )

    assert json.loads(response["HX-Trigger"])["open-modal"] == reverse("edu:specializations:create")


def test_invalid_form_stays_open(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.post(
        reverse("edu:specializations:create"), {"name": "Biology"}, **htmx()
    )

    assert "HX-Trigger" not in response
    assert b"already has a specialization" in response.content


def test_domain_errors_show_on_the_form(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.post(
        reverse("chapters:update", kwargs={"pk": chapter.pk}),
        {
            "name": chapter.name,
            "max_students": 99_999,
        },
        **htmx(),
    )

    assert "HX-Trigger" not in response
    assert b"cannot exceed" in response.content


def test_delete_asks_then_deletes(admin_client: Client, chapter: Chapter) -> None:
    contract = Contract.objects.get(chapter=chapter, employee__name="Ola")
    url = reverse("hr:contracts:delete", kwargs={"pk": contract.pk})

    confirm = admin_client.get(url, **htmx())
    assert b"Ola" in confirm.content
    assert Contract.objects.filter(pk=contract.pk).exists()

    response = admin_client.post(url, {"confirmed": "1", "ids": [contract.pk]}, **htmx())

    assert json.loads(response["HX-Trigger"])["refresh"] is True
    assert not Contract.objects.filter(pk=contract.pk).exists()


def test_bulk_delete_refuses_used_specializations(admin_client: Client, chapter: Chapter) -> None:
    ids = list(Specialization.objects.filter(chapter=chapter).values_list("pk", flat=True))

    response = admin_client.post(
        reverse("edu:specializations:bulk-delete"),
        {"confirmed": "1", "ids": ids},
        **htmx(),
    )

    assert response.status_code == 200
    assert b"still in use" in response.content
    assert Specialization.objects.filter(chapter=chapter).count() == 6


def test_toggle(admin_client: Client, chapter: Chapter) -> None:
    contract = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")

    response = admin_client.post(
        reverse("hr:contracts:toggle", kwargs={"pk": contract.pk}), **htmx()
    )

    contract.refresh_from_db()
    assert not contract.is_active
    assert json.loads(response["HX-Trigger"]) == {"refresh": True}


def test_rows_of_another_chapter_are_not_found(admin_client: Client, chapter: Chapter) -> None:
    other = Chapter.objects.create(name="other")
    faculty = Faculty.objects.create(chapter=other, name="Law", students_per_phd=10)

    response = admin_client.get(
        reverse("edu:faculties:details", kwargs={"pk": faculty.pk}), **htmx()
    )

    assert response.status_code == 404


def test_the_header_switches_chapters(admin_client: Client, chapter: Chapter) -> None:
    other = Chapter.objects.create(name="other")

    admin_client.post(reverse("chapters:select"), {"chapter": other.pk, "next": "/"})

    html = HTMLParser(admin_client.get(reverse("board:dashboard")).content)
    assert html.css_first("#chapter-switcher option[selected]").text(strip=True).startswith("other")


def test_chapter_pages_redirect_without_a_chapter(admin_client: Client) -> None:
    response = admin_client.get(reverse("edu:faculties:index"))

    assert response.status_code == 302
    assert response.url == reverse("chapters:index")


def test_export_xlsx_and_csv(admin_client: Client, chapter: Chapter) -> None:
    xlsx = admin_client.get(reverse("edu:faculties:index"), {"export": "xlsx"})
    csv = admin_client.get(reverse("edu:faculties:index"), {"export": "csv"})

    assert xlsx["Content-Type"].startswith("application/vnd.openxmlformats")
    assert "attachment" in xlsx["Content-Disposition"]
    assert "Dentistry" in csv.content.decode()
    assert "Biology; Medicine" in csv.content.decode()  # Dentistry's supported ones


def test_import_adds_and_updates_by_name(admin_client: Client, chapter: Chapter) -> None:
    content = (
        "name,specialization,is_active,notes\nDr. Sami,Dentistry,1,updated\nDr. New,Biology,1,\n"
    )

    upload = _upload("employees.csv", content)

    response = admin_client.post(reverse("hr:employees:import"), {"file": upload}, **htmx())

    assert json.loads(response["HX-Trigger"])["refresh"] is True
    assert chapter.employees.get(name="Dr. Sami").notes == "updated"
    assert chapter.employees.filter(name="Dr. New").exists()


def test_import_is_all_or_nothing(admin_client: Client, chapter: Chapter) -> None:
    content = "name,specialization,is_active,notes\nDr. Good,Biology,1,\nDr. Bad,Astrology,1,\n"

    response = admin_client.post(
        reverse("hr:employees:import"),
        {"file": _upload("employees.csv", content)},
        **htmx(),
    )

    assert "HX-Trigger" not in response
    assert b"Astrology" in response.content
    assert not chapter.employees.filter(name="Dr. Good").exists()


def _upload(name: str, content: str) -> object:
    from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: PLC0415

    return SimpleUploadedFile(name, content.encode(), content_type="text/csv")


@pytest.mark.parametrize("url_name", TABLES)
def test_tables_remember_their_filters_but_reset_starts_fresh(
    admin_client: Client,
    chapter: Chapter,
    url_name: str,
) -> None:
    html = HTMLParser(admin_client.get(reverse(url_name)).content)

    assert html.css_first("form#filters-form[data-remember-url]") is not None
    assert html.css_first(f"aside a[href='{reverse(url_name)}'][data-url-reset]") is not None


def test_the_filters_button_counts_only_the_filters_applied(
    admin_client: Client, chapter: Chapter
) -> None:
    url = reverse("hr:contracts:index")

    sorted_only = HTMLParser(admin_client.get(url, {"ordering": "-position"}).content)
    filtered = HTMLParser(
        admin_client.get(url, {"degree": "master", "q": "a", "ordering": "-position"}).content
    )

    assert sorted_only.css_first("#filters-badge").text(strip=True) == ""
    assert not sorted_only.css("#filters-reset a")
    assert filtered.css_first("#filters-badge").text(strip=True) == "1"
    # the reset clears the filters only: the search and the sorting stay
    reset = filtered.css_first("#filters-reset a").attributes["href"]
    assert reset == f"{url}?q=a&ordering=-position"


@pytest.mark.parametrize("value", ["abc", "", "999999"])
def test_the_header_refuses_what_is_not_a_chapter(
    admin_client: Client, chapter: Chapter, value: str
) -> None:
    response = admin_client.post(reverse("chapters:select"), {"chapter": value, "next": "/"})

    assert response.status_code == 404


# --- when a request fails -----------------------------------------------------------------


def test_a_refused_page_says_so(viewer_client: Client, chapter: Chapter) -> None:
    response = viewer_client.get(reverse("edu:faculties:create"))

    assert response.status_code == 403
    assert "not allowed" in HTMLParser(response.content).css_first("main").text()


def test_an_unknown_address_says_so(admin_client: Client, client: Client) -> None:
    for visitor in (admin_client, client):  # logged in or not: the page needs no user
        response = visitor.get("/no/such/page/")

        assert response.status_code == 404
        assert "nothing at this address" in HTMLParser(response.content).css_first("main").text()


@pytest.mark.django_db
def test_the_server_error_page_needs_nothing(client: Client) -> None:
    client.raise_request_exception = False

    with mock.patch("unicap.app.views.search.search_everything", side_effect=RuntimeError):
        admin = User.objects.create_superuser("root", password="password")  # noqa: S106
        client.force_login(admin)
        response = client.get(reverse("search"), {"q": "x"})

    assert response.status_code == 500
    assert "went wrong" in response.content.decode()


@pytest.mark.parametrize("status", ["403", "404", "offline", "error"])
def test_every_page_holds_the_toast_of_a_failed_htmx_request(
    admin_client: Client, chapter: Chapter, status: str
) -> None:
    html = HTMLParser(admin_client.get(reverse("board:dashboard")).content)

    assert html.css_first(f'template[data-error-toast="{status}"]') is not None
