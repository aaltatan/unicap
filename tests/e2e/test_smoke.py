"""What only a browser can tell: the Alpine components, the pointer and the keyboard."""

import pytest
from playwright.sync_api import Page, expect

from tests.factories import EmployeeFactory
from unicap.app.models import Chapter, Contract, EmployeeSettings, Faculty

pytestmark = pytest.mark.slow

MODAL = "#modal-container"
ROWS = "#table tbody tr"


def press(page: Page, key: str, code: str, *, alt: bool = False, ctrl: bool = False) -> None:
    """A real key press of another layout: `key` is what it types, `code` where it sits."""
    session = page.context.new_cdp_session(page)
    modifiers = (1 if alt else 0) | (2 if ctrl else 0)

    for kind in ("keyDown", "keyUp"):
        session.send(
            "Input.dispatchKeyEvent",
            {"type": kind, "key": key, "code": code, "modifiers": modifiers},
        )


# --- forms ----------------------------------------------------------------------------------


def test_each_search_box_lists_its_own_rows(page: Page, chapter: Chapter) -> None:
    EmployeeFactory(
        chapter=chapter, specialization=chapter.specializations.first(), name="Dr. Free"
    )
    faculties = set(chapter.faculties.values_list("name", flat=True))

    page.goto("/hr/contracts/")
    page.click("button.btn-primary[hx-get$='/create/']")

    employee = page.locator(f"{MODAL} #id_employee")
    employee.click()
    options = page.locator(f"{MODAL} [data-search-select]").first.locator("li[role=option]")

    expect(options.filter(has_text="Dr. Free")).to_have_count(1)
    assert not faculties & {text.strip() for text in options.all_inner_texts()}

    options.filter(has_text="Dr. Free").click()

    expect(employee).to_have_value("Dr. Free · " + chapter.specializations.first().name)
    assert page.locator(f"{MODAL} select[name=faculty]").input_value() == ""

    page.locator(f"{MODAL} #id_faculty").click()
    listed = page.locator(f"{MODAL} [data-search-select]").nth(1).locator("li[role=option]")

    assert faculties <= {text.strip() for text in listed.all_inner_texts()}


@pytest.mark.parametrize(("size", "width"), [("md", 512), ("xl", 896)])
def test_a_modal_opens_as_wide_as_its_setting(
    page: Page,
    chapter: Chapter,
    size: str,
    width: int,
) -> None:
    EmployeeSettings.objects.update_or_create(pk=1, defaults={"details_modal_size": size})

    page.goto("/hr/employees/")
    page.locator(f"{ROWS} td[data-col=name] button").first.click()

    card = page.locator(f"{MODAL} .card")
    expect(card).to_be_visible()

    assert round(card.bounding_box()["width"]) == width


# --- tables ---------------------------------------------------------------------------------


def test_a_right_click_opens_the_rows_menu_at_the_pointer(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/employees/")

    row = page.locator(ROWS).nth(1)
    cell = row.locator("td[data-col=status]")
    box = cell.bounding_box()
    x, y = box["x"] + 10, box["y"] + box["height"] / 2

    page.mouse.click(x, y, button="right")

    menu = row.locator("[role=menu]")
    expect(menu).to_be_visible()
    expect(menu.locator("[role=menuitem]")).to_have_text(["details", "edit", "delete"])

    placed = menu.bounding_box()
    assert abs(placed["x"] - x) < 2
    assert abs(placed["y"] - y) < 2

    # another row's right click moves the menu there; a click elsewhere closes it
    page.locator(ROWS).nth(3).locator("td[data-col=status]").click(button="right")

    expect(menu).to_be_hidden()
    expect(page.locator(f"{ROWS} [role=menu]:visible")).to_have_count(1)

    page.locator("header h1").click()

    expect(page.locator(f"{ROWS} [role=menu]:visible")).to_have_count(0)


def test_a_double_click_on_a_row_opens_its_edit_form(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/employees/")

    row = page.locator(ROWS).first
    name = row.locator("td[data-col=name] button").inner_text()

    row.locator("td[data-col=status]").dblclick()

    expect(page.locator(f"{MODAL} input[name=name]")).to_have_value(name)


def test_a_related_cell_opens_that_rows_modal(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/employees/")

    link = page.locator(f"{ROWS} td[data-col=faculty] button").first
    faculty = link.inner_text()
    link.click()

    expect(page.locator(f"{MODAL} h2")).to_have_text(faculty)


# --- keyboard and pointer ---------------------------------------------------------------------


def test_shortcuts_work_on_an_arabic_keyboard(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/employees/")
    page.locator("header h1").click()

    press(page, "ظ", "Slash")  # "/" on an Arabic layout

    search = page.locator("main input[name=q]")

    expect(search).to_be_focused()
    expect(search).to_have_value("")  # the letter is not typed

    page.locator("header h1").click()
    press(page, "ى", "KeyN", alt=True)  # Alt+N

    expect(page.locator(f"{MODAL} input[name=name]")).to_be_visible()


def test_a_title_shows_in_the_popup_not_the_browsers_tooltip(page: Page, chapter: Chapter) -> None:
    page.goto("/reports/capacity/")

    # by position: once hovered the span has no title left to be found by
    cell = page.locator("main tbody tr").first.locator("td").nth(1).locator("span").first
    names = cell.get_attribute("title")
    cell.hover()

    popup = page.locator(".tooltip")
    expect(popup).to_be_visible()
    expect(popup).to_have_text(names, use_inner_text=True)
    assert cell.get_attribute("title") is None

    page.mouse.move(0, 0)

    expect(popup).to_be_hidden()


def test_a_report_exports_from_one_menu(page: Page, chapter: Chapter) -> None:
    page.goto("/reports/capacity/")

    menu = page.locator("main [role=menu]")
    expect(menu).to_be_hidden()

    page.get_by_role("button", name="export").click()

    expect(menu).to_be_visible()
    expect(menu.locator("a")).to_have_count(2)
    assert menu.locator("a").nth(0).get_attribute("href") == "/reports/capacity/docx/"
    assert menu.locator("a").nth(1).get_attribute("href") == "/reports/capacity/pdf/"


def test_dragging_a_card_signs_its_contract(page: Page, chapter: Chapter) -> None:
    contract = Contract.objects.for_chapter(chapter.pk).unsigned().first()
    employee = contract.employee
    target = Faculty.objects.accepting(employee.specialization_id).filter(chapter=chapter).first()

    page.goto("/board/")

    card = page.locator(f".board-card[data-employee='{employee.pk}']")
    lane = page.locator(f"[data-lane='{target.pk}']")
    start, end = card.bounding_box(), lane.bounding_box()

    page.mouse.move(start["x"] + 20, start["y"] + start["height"] / 2)
    page.mouse.down()
    page.mouse.move(end["x"] + 40, end["y"] + 30, steps=15)
    page.mouse.move(end["x"] + 45, end["y"] + 35, steps=5)
    page.mouse.up()

    expect(lane.locator(f".board-card[data-employee='{employee.pk}']")).to_have_count(1)

    contract.refresh_from_db()
    assert contract.faculty == target


# --- requests that fail -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "text"),
    [
        ("/hr/contracts/999999/", "not there any more"),
        ("/reports/templates/x/y/default/", "not there"),
    ],
)
def test_a_failed_htmx_request_shows_a_toast(
    page: Page, chapter: Chapter, url: str, text: str
) -> None:
    page.goto("/hr/contracts/")

    page.evaluate("url => window.htmx.ajax('GET', url, {target: '#modal-container'})", url)

    expect(page.locator("#messages [role=alert]").filter(has_text=text)).to_be_visible()
    expect(page.locator(MODAL)).to_be_empty()
