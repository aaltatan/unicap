"""Specialized / supported: what a teacher's specialization is in the faculty they signed to."""

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.models import (
    Chapter,
    Contract,
    Employee,
    Faculty,
    FacultySpecialization,
    User,
)
from unicap.app.templatetags.domain import specialization_type


def expected_types(chapter: Chapter) -> dict[int, str | None]:
    """Each contract's type, read from its faculty's accepted specializations."""
    accepted = {
        (share.faculty_id, share.specialization_id): share.specialization_type
        for share in FacultySpecialization.objects.filter(faculty__chapter=chapter)
    }

    return {
        contract.pk: accepted.get((contract.faculty_id, contract.employee.specialization_id))
        for contract in Contract.objects.for_chapter(chapter.pk).with_relations()
    }


def test_contracts_are_annotated_with_their_type(chapter: Chapter) -> None:
    rows = Contract.objects.for_chapter(chapter.pk).annotate_specialization_type()

    found = {row.pk: row.specialization_type for row in rows}

    assert found == expected_types(chapter)
    assert {"specialized", "supported"} <= set(found.values())  # the sample holds both


def test_an_unsigned_contract_has_no_type(chapter: Chapter) -> None:
    contract = Contract.objects.for_chapter(chapter.pk).signed().first()

    Contract.objects.move(contract, None)

    row = Contract.objects.annotate_specialization_type().get(pk=contract.pk)
    assert row.specialization_type is None


def test_the_annotation_adds_no_row(chapter: Chapter) -> None:
    contracts = Contract.objects.for_chapter(chapter.pk)

    assert contracts.annotate_specialization_type().count() == contracts.count()


def test_employees_are_annotated_with_their_contracts_type(chapter: Chapter) -> None:
    by_contract = expected_types(chapter)

    rows = Employee.objects.for_chapter(chapter.pk).with_contract().annotate_specialization_type()

    assert {row.contract.pk: row.specialization_type for row in rows} == by_contract


def test_the_domain_and_the_database_agree(chapter: Chapter) -> None:
    snapshot = Chapter.objects.get_snapshot(chapter.pk)
    rows = Contract.objects.for_chapter(chapter.pk).annotate_specialization_type()

    for row in rows:
        contract = snapshot.chapter.contract_of(snapshot.employees[row.employee_id])
        kind = specialization_type(contract)

        assert (kind.value if kind else None) == row.specialization_type


@pytest.mark.parametrize("kind", ["specialized", "supported"])
def test_the_contracts_table_filters_by_type(
    admin_client: Client,
    chapter: Chapter,
    kind: str,
) -> None:
    url = reverse("hr:contracts:index")

    response = admin_client.get(
        url, {"specialization_type": kind, "per_page": 100}, **htmx("table")
    )

    cells = HTMLParser(response.content).css('td[data-col="specialization_type"]')
    wanted = [pk for pk, found in expected_types(chapter).items() if found == kind]

    assert len(cells) == len(wanted) > 0
    assert {cell.text(strip=True) for cell in cells} == {kind}


def test_the_contracts_table_sorts_by_type(admin_client: Client, chapter: Chapter) -> None:
    url = reverse("hr:contracts:index")

    response = admin_client.get(url, {"ordering": "specialization_type"}, **htmx("table"))

    assert response.status_code == 200


def test_tables_show_the_type_in_its_own_column_not_in_the_name(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    tagged = len([found for found in expected_types(chapter).values() if found])

    for url_name, name in (("hr:contracts:index", "employee"), ("hr:employees:index", "name")):
        tree = HTMLParser(admin_client.get(reverse(url_name), {"per_page": 100}).content)

        titles = [
            button.attributes["title"] for button in tree.css(f'td[data-col="{name}"] button')
        ]

        assert not tree.css(
            f'td[data-col="{name}"] .badge-info, td[data-col="{name}"] .badge-warning'
        )
        assert len(tree.css('td[data-col="specialization_type"] .badge')) == tagged
        assert len([t for t in titles if t.endswith(("(specialized)", "(supported)"))]) == tagged


def test_board_cards_tell_the_type_in_their_title(admin_client: Client, chapter: Chapter) -> None:
    tagged = len([found for found in expected_types(chapter).values() if found])

    cards = HTMLParser(admin_client.get(reverse("board:index")).content).css(".board-card")

    titles = [card.attributes["title"].split(" · ")[0] for card in cards]
    assert len([t for t in titles if t.endswith(("(specialized)", "(supported)"))]) == tagged
    assert len([card for card in cards if card.css_first(".badge")]) == tagged


@pytest.mark.parametrize("kind", ["specialized", "supported"])
def test_the_employees_table_filters_by_type(
    admin_client: Client,
    chapter: Chapter,
    kind: str,
) -> None:
    url = reverse("hr:employees:index")

    response = admin_client.get(
        url, {"specialization_type": kind, "per_page": 100}, **htmx("table")
    )

    cells = HTMLParser(response.content).css('td[data-col="specialization_type"]')
    wanted = [pk for pk, found in expected_types(chapter).items() if found == kind]

    assert len(cells) == len(wanted) > 0
    assert {cell.text(strip=True) for cell in cells} == {kind}


def test_related_rows_open_their_own_modal(
    admin_client: Client,
    viewer_client: Client,
    chapter: Chapter,
) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).filter(contracts__isnull=False).first()
    wanted = f'td[data-col="faculty"] button[hx-get="{faculty.get_absolute_url()}"]'

    for url_name in ("hr:employees:index", "hr:contracts:index"):
        for client in (admin_client, viewer_client):  # a viewer may view faculties too
            tree = HTMLParser(client.get(reverse(url_name), {"per_page": 100}).content)

            button = tree.css_first(wanted)
            assert button is not None
            assert button.attributes["hx-target"] == "#modal-container"
            assert tree.css_first('td[data-col="specialization"] button[hx-get]') is not None


def test_a_related_row_is_plain_text_without_the_right_to_view_it(
    client: Client,
    chapter: Chapter,
) -> None:
    user = User.objects.create_user("contracts-only", password="password")  # noqa: S106
    user.user_permissions.set(Permission.objects.filter(codename="view_contract"))
    client.force_login(user)

    tree = HTMLParser(client.get(reverse("hr:contracts:index"), {"per_page": 100}).content)

    assert tree.css('td[data-col="faculty"]')
    assert not tree.css('td[data-col="faculty"] button')
    assert not tree.css('td[data-col="specialization"] button')


def test_the_print_page_has_a_type_column(admin_client: Client, chapter: Chapter) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).filter(contracts__isnull=False).first()

    response = admin_client.get(reverse("reports:staff", args=(faculty.pk,)))

    table = HTMLParser(response.content).css_first("table")
    headers = [th.text(strip=True) for th in table.css("thead th")]
    column = headers.index("specialization type")
    types = {row.css("td")[column].text(strip=True) for row in table.css("tbody tr")}

    assert types <= {"specialized", "supported", ""}
    assert types & {"specialized", "supported"}
