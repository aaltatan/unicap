"""Searching (any word order, Arabic spellings), the rows' "⋮" menu, and bulk actions."""

import pytest
from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.models import Chapter, Contract, Faculty, Specialization
from unicap.app.utils import normalize, search_terms

ARCHITECTURE = "هندسة العمارة والتخطيط العمراني"


# --- search -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "same"),
    [
        ("إدارة الأعمال", "اداره الاعمال"),
        ("مُعَلِّم", "معلم"),
        ("مستشفى", "مستشفي"),
        ("Biology", "biology"),
    ],
)
def test_spellings_compare_equal(text: str, same: str) -> None:
    assert normalize(text) == normalize(same)


def test_a_leading_article_is_dropped_from_long_words() -> None:
    assert search_terms("العمارة وال") == ["عماره", "وال"]


@pytest.mark.parametrize(
    "query",
    ["هند عمار", "عمارة هندسة", "هند عمراني", "العمارة", "التخطيط هندسه", "عمراني هند"],
)
def test_words_in_any_order_find_a_name(chapter: Chapter, query: str) -> None:
    Specialization.objects.create(chapter=chapter, name=ARCHITECTURE)

    found = Specialization.objects.for_chapter(chapter.pk).search(query)

    assert ARCHITECTURE in found.values_list("name", flat=True)


@pytest.mark.parametrize("query", ["هند طب", "!عمار هند"])
def test_every_word_must_match(chapter: Chapter, query: str) -> None:
    Specialization.objects.create(chapter=chapter, name=ARCHITECTURE)

    found = Specialization.objects.for_chapter(chapter.pk).search(query)

    assert ARCHITECTURE not in found.values_list("name", flat=True)


def test_the_header_searches_everything(admin_client: Client, chapter: Chapter) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).get(name="Dentistry")

    response = admin_client.get(reverse("search"), {"q": "dent"})

    html = HTMLParser(response.content)
    assert html.css_first(f"button[hx-get='{faculty.get_absolute_url()}']")
    assert "Dentistry" in html.text()


def test_the_header_search_shows_only_what_the_user_may_see(
    client: Client,
    chapter: Chapter,
) -> None:
    from unicap.app.models import User  # noqa: PLC0415

    user = User.objects.create_user("faculties-only", password="password")  # noqa: S106
    user.user_permissions.add(*_permissions("view_faculty"))
    client.force_login(user)

    text = HTMLParser(client.get(reverse("search"), {"q": "e"}).content).text()

    assert "Dentistry" in text
    assert "Dr. Sami" not in text  # an employee


# --- the rows' menu -----------------------------------------------------------------------


def test_each_row_has_its_actions_under_one_button(admin_client: Client, chapter: Chapter) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).first()

    html = HTMLParser(admin_client.get(reverse("edu:faculties:index")).content)
    menu = html.css_first("#table [x-data='rowMenu']")

    assert menu.css_first("button[x-ref='button']") is not None
    links = {
        node.attributes.get("hx-get") or node.attributes.get("href")
        for node in menu.css("[role='menuitem']")
    }
    assert faculty.get_absolute_url() in links
    assert faculty.get_update_url() in links


def test_the_menu_offers_only_what_the_user_may_do(viewer_client: Client, chapter: Chapter) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).first()

    html = HTMLParser(viewer_client.get(reverse("edu:faculties:index")).content)

    assert html.css_first(f"#table [hx-get='{faculty.get_absolute_url()}']") is not None
    assert html.css_first(f"#table [hx-get='{faculty.get_update_url()}']") is None
    assert html.css_first(f"#table [hx-get='{faculty.get_delete_url()}']") is None


# --- bulk actions -------------------------------------------------------------------------


def bulk_action(client: Client, url_name: str, action: str, ids: list[int]) -> object:
    return client.post(
        reverse(url_name),
        {"action": action, "ids": ids, "confirmed": "1"},
        **htmx(),
    )


def test_a_bulk_action_asks_first(admin_client: Client, chapter: Chapter) -> None:
    ids = list(chapter.specializations.values_list("pk", flat=True)[:2])

    response = admin_client.post(
        reverse("edu:specializations:bulk-action"),
        {"action": "deactivate", "ids": ids},
        **htmx(),
    )

    assert response.status_code == 200
    assert chapter.specializations.filter(pk__in=ids, is_active=True).count() == len(ids)


def test_selected_specializations_are_switched_off(admin_client: Client, chapter: Chapter) -> None:
    ids = list(chapter.specializations.values_list("pk", flat=True)[:2])

    bulk_action(admin_client, "edu:specializations:bulk-action", "deactivate", ids)

    assert not chapter.specializations.filter(pk__in=ids, is_active=True).exists()
    assert chapter.specializations.exclude(pk__in=ids).filter(is_active=True).exists()


def test_selected_faculties_accept_nothing_any_more(admin_client: Client, chapter: Chapter) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).filter(shares__isnull=False).first()

    bulk_action(admin_client, "edu:faculties:bulk-action", "clear-shares", [faculty.pk])

    assert not faculty.shares.exists()


def test_selected_contracts_are_unsigned_together(admin_client: Client, chapter: Chapter) -> None:
    ids = list(chapter.contracts.exclude(faculty=None).values_list("pk", flat=True))

    bulk_action(admin_client, "hr:contracts:bulk-action", "unsign", ids)

    assert not Contract.objects.filter(pk__in=ids).exclude(faculty=None).exists()


def test_bulk_edit_changes_only_the_checked_fields(admin_client: Client, chapter: Chapter) -> None:
    faculties = Faculty.objects.for_chapter(chapter.pk)
    ids = list(faculties.values_list("pk", flat=True))
    per_phd = {f.pk: f.students_per_phd for f in faculties}

    response = admin_client.post(
        reverse("edu:faculties:bulk-edit"),
        {
            "ids": ids,
            "confirmed": "1",
            "apply_current_students": "on",
            "current_students": "40",
            "students_per_phd": "999",  # not checked: unchanged
        },
        **htmx(),
    )

    assert "HX-Trigger" in response
    assert set(faculties.values_list("current_students", flat=True)) == {40}
    assert {f.pk: f.students_per_phd for f in faculties} == per_phd


def test_a_bulk_edit_breaking_a_rule_changes_nothing(
    admin_client: Client, chapter: Chapter
) -> None:
    fulltime_staff = chapter.contracts.filter(contract_type="fulltime", employment_type="staff")
    ids = list(fulltime_staff.values_list("pk", flat=True))

    response = admin_client.post(
        reverse("hr:contracts:bulk-edit"),
        {"ids": ids, "confirmed": "1", "apply_contract_type": "on", "contract_type": "parttime"},
        **htmx(),
    )

    assert "HX-Trigger" not in response
    assert "always borrowed" in response.content.decode()  # the reason is shown
    assert fulltime_staff.count() == len(ids)  # nothing changed


def test_rows_of_another_chapter_are_left_alone(admin_client: Client, chapter: Chapter) -> None:
    other = Chapter.objects.create(name="other")
    foreign = Specialization.objects.create(chapter=other, name="Elsewhere")

    bulk_action(admin_client, "edu:specializations:bulk-action", "deactivate", [foreign.pk])

    foreign.refresh_from_db()
    assert foreign.is_active


def test_bulk_changes_need_the_change_permission(viewer_client: Client, chapter: Chapter) -> None:
    ids = list(chapter.specializations.values_list("pk", flat=True))

    response = bulk_action(viewer_client, "edu:specializations:bulk-action", "deactivate", ids)

    assert response.status_code == 403


def _permissions(*codenames: str) -> list[object]:
    from django.contrib.auth.models import Permission  # noqa: PLC0415

    return list(Permission.objects.filter(codename__in=codenames))
