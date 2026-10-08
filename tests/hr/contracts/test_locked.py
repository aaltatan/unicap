"""A locked contract stays in its faculty, whatever would move it."""

import json

import pytest
from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser
from tablib import Dataset

from tests.conftest import htmx
from unicap.app import resources
from unicap.app.backups import service
from unicap.app.exceptions import UserError
from unicap.app.models import Chapter, Contract, Faculty
from unicap.domain import Strategy


@pytest.fixture
def sami(chapter: Chapter) -> Contract:
    """Dr. Sami, signed to Dentistry and locked there."""
    contract = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")
    contract.is_locked = True
    return Contract.objects.save_contract(contract)


@pytest.fixture
def pharmacy(chapter: Chapter) -> Faculty:
    return Faculty.objects.get(chapter=chapter, name="Pharmacy")


def _faculty_name(contract: Contract) -> str | None:
    contract.refresh_from_db()
    return contract.faculty.name if contract.faculty else None


# --- querysets and managers ---------------------------------------------------------------


def test_pinned_and_movable(chapter: Chapter, sami: Contract) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")  # unsigned
    Contract.objects.filter(pk=karim.pk).update(is_locked=True)

    rows = Contract.objects.for_chapter(chapter.pk)

    assert list(rows.pinned()) == [sami]  # locked but unsigned is not pinned yet
    assert rows.movable().count() == rows.count() - 1
    assert karim in rows.movable()


@pytest.mark.parametrize("to_pharmacy", [True, False])
def test_move_is_refused(sami: Contract, pharmacy: Faculty, to_pharmacy: bool) -> None:  # noqa: FBT001
    with pytest.raises(UserError, match=r"Dr\. Sami \(Dentistry\)"):
        Contract.objects.move(sami, pharmacy.pk if to_pharmacy else None)

    assert _faculty_name(sami) == "Dentistry"


def test_a_locked_unsigned_contract_is_signed_then_stays(
    chapter: Chapter, pharmacy: Faculty
) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")
    karim.is_locked = True
    Contract.objects.save_contract(karim)

    Contract.objects.move(karim, pharmacy.pk)
    assert _faculty_name(karim) == "Pharmacy"

    with pytest.raises(UserError):
        Contract.objects.move(karim, None)


def test_unlocking_and_moving_in_one_save(sami: Contract, pharmacy: Faculty) -> None:
    sami.is_locked = False
    sami.faculty = pharmacy

    Contract.objects.save_contract(sami)

    assert _faculty_name(sami) == "Pharmacy"


def test_everything_else_of_a_locked_contract_still_changes(sami: Contract) -> None:
    sami.notes = "stays in Dentistry"

    Contract.objects.save_contract(sami)
    Contract.objects.toggle_active(sami)

    sami.refresh_from_db()
    assert (sami.notes, sami.is_active) == ("stays in Dentistry", False)


def test_bulk_moves_are_refused_unless_they_unlock(
    chapter: Chapter, sami: Contract, pharmacy: Faculty
) -> None:
    lina = Contract.objects.get(chapter=chapter, employee__name="Dr. Lina")
    ids = [sami.pk, lina.pk]

    for values in ({"faculty": pharmacy}, {"faculty": None}):
        with pytest.raises(UserError, match=r"Dr\. Sami"):
            Contract.objects.bulk_set(chapter.pk, ids, values)

    assert (_faculty_name(sami), _faculty_name(lina)) == ("Dentistry", "Dentistry")

    Contract.objects.bulk_set(chapter.pk, [sami.pk], {"faculty": None, "is_locked": False})

    assert _faculty_name(sami) is None


def test_reset_leaves_locked_contracts_signed(chapter: Chapter, sami: Contract) -> None:
    assert Chapter.objects.reset(chapter) == 13

    assert list(Contract.objects.for_chapter(chapter.pk).signed()) == [sami]


def test_placements_moving_a_locked_contract_are_refused(
    chapter: Chapter, sami: Contract, pharmacy: Faculty
) -> None:
    lina = Contract.objects.get(chapter=chapter, employee__name="Dr. Lina")

    with pytest.raises(UserError, match=r"Dr\. Sami"):
        Chapter.objects.apply_placements(chapter, {lina.pk: None, sami.pk: pharmacy.pk})

    assert _faculty_name(lina) == "Dentistry"  # nothing is saved

    assert Chapter.objects.apply_placements(chapter, {sami.pk: sami.faculty_id}) == 0


@pytest.mark.parametrize("strategy", list(Strategy))
def test_the_optimizer_keeps_it(chapter: Chapter, sami: Contract, strategy: Strategy) -> None:
    Contract.objects.for_chapter(chapter.pk).exclude(pk=sami.pk).update(faculty=None)

    optimization = Chapter.objects.get_snapshot(chapter.pk).optimization(strategy)

    assert optimization.placements[sami.pk] == sami.faculty_id
    assert all(move.employee.name != "Dr. Sami" for move in optimization.moves)


def test_the_lock_is_translated_both_ways(chapter: Chapter, sami: Contract) -> None:
    value = sami.to_domain()

    assert value.is_locked
    assert value.is_pinned
    assert Contract.from_domain(value, faculty_id=sami.faculty_id).is_locked


def test_a_duplicated_chapter_keeps_the_locks(chapter: Chapter, sami: Contract) -> None:
    copy = Chapter.objects.duplicate(chapter, "copy")

    assert list(copy.contracts.pinned().values_list("employee__name", flat=True)) == ["Dr. Sami"]


# --- files --------------------------------------------------------------------------------


def test_an_import_cannot_move_a_locked_contract(chapter: Chapter, sami: Contract) -> None:
    resource = resources.ContractResource(chapter=chapter)

    moved = Dataset(headers=["employee", "faculty", "is_locked"])
    moved.append(["Dr. Sami", "Pharmacy", "1"])

    with pytest.raises(UserError, match="locked"):
        Contract.objects.import_rows(resource, moved)

    unlocked = Dataset(headers=["employee", "faculty", "is_locked"])
    unlocked.append(["Dr. Sami", "Pharmacy", "0"])

    assert Contract.objects.import_rows(resource, unlocked) == 1
    assert _faculty_name(sami) == "Pharmacy"


def test_the_export_holds_the_lock(admin_client: Client, chapter: Chapter, sami: Contract) -> None:
    response = admin_client.get(reverse("hr:contracts:index"), {"export": "csv"})

    rows = Dataset().load(response.content.decode("utf-8-sig"), format="csv").dict

    assert {row["employee"]: row["locked to its faculty"] for row in rows}["Dr. Sami"] == "yes"
    assert {row["locked to its faculty"] for row in rows} == {"yes", "no"}


def test_a_backup_brings_the_lock_back(chapter: Chapter, sami: Contract) -> None:
    backup = service.create("section", chapter=chapter, section="contracts")

    Contract.objects.filter(pk=sami.pk).update(is_locked=False, faculty=None)

    service.restore(backup)

    sami.refresh_from_db()
    assert sami.is_locked
    assert _faculty_name(sami) == "Dentistry"


# --- pages --------------------------------------------------------------------------------


def test_the_form_locks_a_contract(admin_client: Client, chapter: Chapter) -> None:
    lina = Contract.objects.get(chapter=chapter, employee__name="Dr. Lina")

    form = HTMLParser(admin_client.get(lina.get_update_url(), **htmx()).content)
    assert form.css_first("input[name=is_locked]") is not None

    admin_client.post(
        lina.get_update_url(),
        {
            "employee": lina.employee_id,
            "faculty": lina.faculty_id,
            "degree": lina.degree,
            "contract_type": lina.contract_type,
            "employment_type": lina.employment_type,
            "is_active": "on",
            "is_locked": "on",
        },
        **htmx(),
    )

    lina.refresh_from_db()
    assert lina.is_locked


def test_the_form_says_why_a_locked_contract_does_not_move(
    admin_client: Client, sami: Contract, pharmacy: Faculty
) -> None:
    response = admin_client.post(
        sami.get_update_url(),
        {
            "employee": sami.employee_id,
            "faculty": pharmacy.pk,
            "degree": sami.degree,
            "contract_type": sami.contract_type,
            "employment_type": sami.employment_type,
            "is_active": "on",
            "is_locked": "on",
        },
        **htmx(),
    )

    assert "HX-Trigger" not in response
    assert "locked to their faculty" in response.content.decode()
    assert _faculty_name(sami) == "Dentistry"


def test_the_table_shows_and_filters_the_lock(
    admin_client: Client, chapter: Chapter, sami: Contract
) -> None:
    url = reverse("hr:contracts:index")

    locked = HTMLParser(admin_client.get(url, {"is_locked": "1"}, **htmx("table")).content)
    free = HTMLParser(admin_client.get(url, {"is_locked": "0"}, **htmx("table")).content)

    def switches(html: HTMLParser) -> set[str | None]:
        return {
            node.attributes["aria-checked"]
            for node in html.css("td[data-col=is_locked] button[role=switch]")
        }

    assert len(locked.css("tbody tr")) == 1
    assert switches(locked) == {"true"}
    assert len(free.css("tbody tr")) == 15
    assert switches(free) == {"false"}


def test_the_lock_is_a_switch_like_the_on_off_one(
    admin_client: Client, viewer_client: Client, chapter: Chapter
) -> None:
    lina = Contract.objects.get(chapter=chapter, employee__name="Dr. Lina")
    url = reverse("hr:contracts:toggle-lock", kwargs={"pk": lina.pk})

    row = HTMLParser(
        admin_client.get(reverse("hr:contracts:index"), {"q": "Lina"}, **htmx("table")).content
    )
    switch = row.css_first("td[data-col=is_locked] button[role=switch]")

    assert switch.attributes["hx-post"] == url == lina.get_toggle_lock_url()

    response = admin_client.post(url, **htmx())

    lina.refresh_from_db()
    assert lina.is_locked
    assert json.loads(response["HX-Trigger"]) == {"refresh": True}  # tables and board redraw

    admin_client.post(url, **htmx())

    lina.refresh_from_db()
    assert not lina.is_locked

    # a viewer sees it, cannot switch it
    seen = HTMLParser(
        viewer_client.get(reverse("hr:contracts:index"), {"q": "Lina"}, **htmx("table")).content
    ).css_first("td[data-col=is_locked] button[role=switch]")

    assert "disabled" in seen.attributes
    assert "hx-post" not in seen.attributes
    assert viewer_client.post(url).status_code == 403
    assert admin_client.get(url).status_code == 405


def test_the_switch_says_which_way_it_went(admin_client: Client, chapter: Chapter) -> None:
    lina = Contract.objects.get(chapter=chapter, employee__name="Dr. Lina")
    url = lina.get_toggle_lock_url()

    locked = admin_client.post(url, **htmx()).content.decode()
    unlocked = admin_client.post(url, **htmx()).content.decode()

    assert "Dr. Lina is locked to its faculty." in locked
    assert "Dr. Lina is unlocked." in unlocked


@pytest.mark.parametrize(("action", "expected"), [("lock", 2), ("unlock", 0)])
def test_bulk_lock_and_unlock(
    admin_client: Client, chapter: Chapter, sami: Contract, action: str, expected: int
) -> None:
    lina = Contract.objects.get(chapter=chapter, employee__name="Dr. Lina")

    admin_client.post(
        reverse("hr:contracts:bulk-action"),
        {"action": action, "ids": [sami.pk, lina.pk], "confirmed": "1"},
        **htmx(),
    )

    assert Contract.objects.for_chapter(chapter.pk).pinned().count() == expected


def test_the_board_does_not_drag_or_drop_a_locked_card(
    admin_client: Client, chapter: Chapter, sami: Contract, pharmacy: Faculty
) -> None:
    response = admin_client.post(
        reverse("board:move"),
        {"employee": sami.employee_id, "faculty": pharmacy.pk},
        **htmx("board"),
    )

    html = HTMLParser(response.content)
    card = html.css_first(f"[data-employee='{sami.employee_id}']")
    free = html.css_first(f"[data-employee='{sami.employee_id + 1}']")

    assert _faculty_name(sami) == "Dentistry"
    assert "x-sort:ignore" in card.attributes
    assert card.css_first("[data-locked]") is not None
    assert "x-sort:ignore" not in free.attributes
    assert free.css_first("[data-locked]") is None


def test_the_reset_says_what_stays(admin_client: Client, chapter: Chapter, sami: Contract) -> None:
    confirm = admin_client.get(reverse("board:reset"), **htmx()).content.decode()

    assert "all 13 signed" in confirm
    assert "1 locked contract stays in its faculty." in confirm

    admin_client.post(reverse("board:reset"), **htmx())

    assert list(Contract.objects.for_chapter(chapter.pk).signed()) == [sami]


def test_optimize_never_posts_a_move_of_a_locked_contract(
    admin_client: Client, chapter: Chapter, sami: Contract
) -> None:
    Contract.objects.for_chapter(chapter.pk).exclude(pk=sami.pk).update(faculty=None)

    preview = admin_client.get(
        reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx()
    )
    placements = HTMLParser(preview.content).css_first("input[name=placements]")

    assert json.loads(placements.attributes["value"])[str(sami.pk)] == sami.faculty_id
