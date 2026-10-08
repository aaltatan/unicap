"""What only a browser can tell: the Alpine components, the pointer and the keyboard."""

import re

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
    lane = page.locator(f"section [data-lane='{target.pk}']")
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


# --- modals take the focus ------------------------------------------------------------------


def test_a_form_modal_focuses_its_first_field(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/employees/")
    page.click("button.btn-primary[hx-get$='/create/']")

    expect(page.locator(f"{MODAL} input[name=name]")).to_be_focused()


def test_a_searched_select_is_a_first_field_too(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/contracts/")
    page.click("button.btn-primary[hx-get$='/create/']")

    # the text input drawn over the employee's <select>, not the hidden select itself
    expect(page.locator(f"{MODAL} #id_employee")).to_be_focused()


def test_a_modal_without_a_field_focuses_its_close_button(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/employees/")
    page.locator(f"{ROWS} td[data-col=name] button").first.click()

    expect(page.locator(f"{MODAL} button[data-modal-close]")).to_be_focused()

    page.keyboard.press("Enter")  # the focused button closes it

    expect(page.locator(f"{MODAL} .card")).to_be_hidden()


def test_a_form_drawn_again_focuses_its_first_field_again(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/employees/")
    page.click("button.btn-primary[hx-get$='/create/']")

    name = page.locator(f"{MODAL} input[name=name]")
    expect(name).to_be_focused()

    page.locator(f"{MODAL} button[type=submit]").first.click()  # empty: drawn again, with errors

    expect(page.locator(f"{MODAL} [aria-invalid]").first).to_be_visible()
    expect(page.locator(f"{MODAL} input[name=name]")).to_be_focused()


# --- clearing the filters -------------------------------------------------------------------


def test_clearing_the_filters_does_not_reload_the_page(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/contracts/?degree=master&q=a")
    page.evaluate("window.stillHere = true")  # gone after a page load

    expect(page.locator(ROWS)).to_have_count(2)

    page.locator("#filters-reset a").click()

    # the filter goes, the search stays; the address and the sidebar's form follow
    expect(page).to_have_url("/hr/contracts/?q=a")
    expect(page.locator("#filters-reset a")).to_have_count(0)
    expect(page.locator("#filters-badge")).to_be_empty()
    expect(page.locator("main input[name=q]")).to_have_value("a")
    assert page.locator("#filters-form input[name=degree]:checked").count() == 0
    assert page.evaluate("window.stillHere") is True

    # the next search does not bring the cleared filter back
    page.locator("main input[name=q]").fill("dr")

    expect(page).to_have_url(re.compile(r"[?&]q=dr(&|$)"))
    assert "degree" not in page.url


def test_the_sidebars_reset_clears_the_search_too(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/contracts/?degree=master&q=a")
    page.evaluate("window.stillHere = true")

    page.get_by_role("button", name="filters").click()
    page.locator("aside a[data-url-reset]").click()

    expect(page).to_have_url("/hr/contracts/")
    expect(page.locator(ROWS)).to_have_count(16)
    expect(page.locator("main input[name=q]")).to_have_value("")
    assert page.locator("#filters-form input[name=degree]:checked").count() == 0
    assert page.evaluate("window.stillHere") is True


def test_no_match_offers_to_clear_the_filters_in_place(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/contracts/?q=zzz-no-such")
    page.evaluate("window.stillHere = true")

    page.locator("#table a[data-url-reset]").click()

    expect(page.locator(ROWS)).to_have_count(16)
    expect(page.locator("main input[name=q]")).to_have_value("")
    assert page.evaluate("window.stillHere") is True


# --- locked contracts and substitutes -------------------------------------------------------


def test_a_locked_card_is_not_dragged(page: Page, chapter: Chapter) -> None:
    contract = Contract.objects.get(chapter=chapter, employee__name="Dr. Fadi")
    Contract.objects.filter(pk=contract.pk).update(is_locked=True)

    page.goto("/board/")

    card = page.locator(f".board-card[data-employee='{contract.employee_id}']")
    lane = page.locator("section [data-lane='unsigned']")
    start, end = card.bounding_box(), lane.bounding_box()

    page.mouse.move(start["x"] + 20, start["y"] + start["height"] / 2)
    page.mouse.down()
    page.mouse.move(end["x"] + 40, end["y"] + 30, steps=15)
    page.mouse.move(end["x"] + 45, end["y"] + 35, steps=5)
    page.mouse.up()

    expect(lane.locator(f".board-card[data-employee='{contract.employee_id}']")).to_have_count(0)
    expect(card.locator("[data-locked]")).to_be_visible()

    contract.refresh_from_db()
    assert contract.faculty.name == "Pharmacy"


def test_a_move_is_applied_with_the_employee_chosen(page: Page, chapter: Chapter) -> None:
    maya = Contract.objects.get(chapter=chapter, employee__name="Dr. Maya")

    page.goto("/board/")
    page.evaluate(
        "window.htmx.ajax('GET', '/board/optimize/?strategy=maximize_students',"
        " {target: '#modal-container'})"
    )

    selects = page.locator(f"{MODAL} select[name^='substitute-']")
    expect(selects.first).to_be_focused()  # the modal's first field

    # every move has its select; this one lists who else could make it
    select = selects.filter(has=page.locator(f"option[value='{maya.pk}']")).first
    moved = select.locator("option:checked").inner_text()
    select.select_option(str(maya.pk))
    page.locator(f"{MODAL} button[type=submit]").click()

    expect(page.locator(f"{MODAL} .card")).to_be_hidden()

    maya.refresh_from_db()
    assert maya.faculty.name == "Pharmacy"
    assert Contract.objects.get(chapter=chapter, employee__name=moved).faculty.name == "Dentistry"


# --- a form's fields are all in reach -------------------------------------------------------


def test_a_focused_searched_select_does_not_cover_the_next_fields(
    page: Page, chapter: Chapter
) -> None:
    page.goto("/hr/contracts/")
    page.locator(ROWS).first.locator("td[data-col=status]").dblclick()

    employee = page.locator(f"{MODAL} #id_employee")
    expect(employee).to_be_focused()
    # focused, its list stays closed: what is under it can be clicked
    expect(page.locator(f"{MODAL} [role=listbox]:visible")).to_have_count(0)

    chosen = employee.input_value()
    page.locator(f"{MODAL} #id_degree").click()

    expect(page.locator(f"{MODAL} #id_degree")).to_be_focused()
    expect(employee).to_have_value(chosen)

    page.locator(f"{MODAL} #id_notes").click()

    expect(page.locator(f"{MODAL} #id_notes")).to_be_focused()


def test_tab_walks_the_whole_form_and_typing_opens_a_searched_select(
    page: Page, chapter: Chapter
) -> None:
    page.goto("/hr/employees/")
    page.click("button.btn-primary[hx-get$='/create/']")

    expect(page.locator(f"{MODAL} input[name=name]")).to_be_focused()

    visited = []

    for _ in range(6):
        page.keyboard.press("Tab")
        visited.append(page.evaluate("document.activeElement.id"))
        expect(page.locator(f"{MODAL} [role=listbox]:visible")).to_have_count(0)

    assert visited[:2] == ["id_specialization", "id_is_active"]
    assert visited[-1] == "id_notes"

    page.locator(f"{MODAL} #id_specialization").focus()
    page.keyboard.type("bio")

    options = page.locator(f"{MODAL} [role=listbox]:visible li[role=option]")
    expect(options).to_have_text(["Biology"])

    page.keyboard.press("Enter")
    page.keyboard.press("Tab")

    expect(page.locator(f"{MODAL} #id_specialization")).to_have_value("Biology")
    expect(page.locator(f"{MODAL} #id_is_active")).to_be_focused()


def test_a_confirmation_keeps_the_focus_on_its_own_button(page: Page, chapter: Chapter) -> None:
    page.goto("/hr/contracts/")
    row = page.locator(ROWS).first
    row.locator("td[data-col=status]").click(button="right")
    row.locator("[role=menuitem]:visible", has_text="delete").click()

    expect(page.locator(f"{MODAL} button[type=submit]")).to_be_focused()


# --- the board ------------------------------------------------------------------------------


def test_a_right_click_on_a_card_opens_its_menu(page: Page, chapter: Chapter) -> None:
    sami = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")  # fulltime staff

    page.goto("/board/")

    card = page.locator(f".board-card[data-employee='{sami.employee_id}']")
    card.click(button="right")

    menu = page.locator("#card-menu")
    expect(menu).to_be_visible()
    expect(menu.locator("[role=menuitem]:visible")).to_have_text(
        [
            "details",
            "edit",
            "deactivate",
            "lock to its faculty",
            "make it a master",
            "make it parttime",
            "make it borrowed",
        ],
        use_inner_text=True,  # what is shown: each switch holds both of its labels
    )
    # the domain's say, not the page's: fulltime staff cannot become parttime
    expect(menu.locator("[data-switch=contract_type]")).to_be_disabled()
    expect(menu.locator("[data-switch=employment_type]")).to_be_enabled()

    menu.locator("[data-switch=is_active]").click()

    expect(menu).to_be_hidden()
    expect(card).to_have_class(re.compile(r"\bexcluded\b"))

    sami.refresh_from_db()
    assert not sami.is_active

    # the menu follows the card: now it offers to switch it back on
    card.click(button="right")

    expect(menu.locator("[data-switch=is_active]")).to_have_text("activate", use_inner_text=True)

    page.keyboard.press("Escape")

    expect(menu).to_be_hidden()


def test_a_cards_button_opens_the_same_menu(page: Page, chapter: Chapter) -> None:
    nour = Contract.objects.get(chapter=chapter, employee__name="Dr. Nour")  # parttime

    page.goto("/board/")

    card = page.locator(f".board-card[data-employee='{nour.employee_id}']")
    card.hover()
    card.locator("button[data-card-menu]").click()

    menu = page.locator("#card-menu")
    expect(menu).to_be_visible()
    expect(page.locator(f"{MODAL} .card")).to_have_count(0)  # the button is not the card's click
    expect(menu.locator("[data-switch=employment_type]")).to_be_disabled()

    menu.locator("[data-switch=is_locked]").click()

    expect(card.locator("[data-locked]")).to_be_visible()

    nour.refresh_from_db()
    assert nour.is_locked


def test_a_click_on_a_card_opens_its_details_at_once(page: Page, chapter: Chapter) -> None:
    sami = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")

    page.goto("/board/")
    page.locator(f".board-card[data-employee='{sami.employee_id}'] span").first.click()

    expect(page.locator(f"{MODAL} h2")).to_have_text("Dr. Sami")


def test_a_double_click_on_a_lane_opens_its_facultys_form(page: Page, chapter: Chapter) -> None:
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    page.goto("/board/")
    page.locator(f"section[data-key='{pharmacy.pk}'] header p").first.dblclick()

    expect(page.locator(f"{MODAL} input[name=name]")).to_have_value("Pharmacy")
    expect(page.locator(f"{MODAL} input[name=name]")).to_be_focused()


def test_the_dock_signs_a_card_without_scrolling(page: Page, chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")  # unsigned
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    page.goto("/board/")

    dock = page.locator("[data-dock]")
    expect(dock).to_be_hidden()

    card = page.locator(f".board-card[data-employee='{karim.employee_id}']")
    start = card.bounding_box()

    page.mouse.move(start["x"] + 20, start["y"] + start["height"] / 2)
    page.mouse.down()
    page.mouse.move(start["x"] + 40, start["y"] + 40, steps=5)

    expect(dock).to_be_visible()

    target = dock.locator(f".dock-target[data-lane='{pharmacy.pk}']")
    end = target.bounding_box()

    page.mouse.move(end["x"] + end["width"] / 2, end["y"] + end["height"] / 2, steps=15)
    page.mouse.move(end["x"] + end["width"] / 2 + 3, end["y"] + end["height"] / 2 + 3, steps=5)

    expect(target).to_have_class(re.compile(r"\bwould-count\b"))  # as the lane itself would say

    page.mouse.up()

    lane = page.locator(f"section[data-key='{pharmacy.pk}']")
    expect(lane.locator(f".board-card[data-employee='{karim.employee_id}']")).to_have_count(1)
    expect(page.locator("[data-dock]")).to_be_hidden()

    karim.refresh_from_db()
    assert karim.faculty == pharmacy


def test_full_screen_puts_the_lanes_side_by_side(page: Page, chapter: Chapter) -> None:
    page.goto("/board/")

    lanes = page.locator("section.lane")
    button = page.locator("button[data-fullscreen]")

    button.click()

    expect(button).to_have_attribute("aria-pressed", "true")
    # the device's full screen, of the whole page: its modals and toasts are still drawn
    assert page.evaluate("document.fullscreenElement === document.documentElement") is True

    boxes = [lanes.nth(index).bounding_box() for index in range(lanes.count())]

    assert len({round(box["y"]) for box in boxes}) == 1  # one row
    assert [box["x"] for box in boxes] == sorted(box["x"] for box in boxes)
    # over the whole window: the page's header and sidebar are under it
    covered = "document.elementFromPoint(700, 20).closest('header') === null"
    box = page.locator("main [x-data^=board]").bounding_box()

    assert (box["x"], box["y"]) == (0, 0)
    assert page.evaluate(covered) is True

    # a modal still opens over it
    page.locator(".board-card span").first.click()
    expect(page.locator(f"{MODAL} .card")).to_be_visible()
    page.locator(f"{MODAL} button[data-modal-close]").click()
    expect(page.locator(f"{MODAL} .card")).to_be_hidden()

    button.click()

    expect(button).to_have_attribute("aria-pressed", "false")
    assert page.evaluate("document.fullscreenElement") is None
    assert page.evaluate(covered) is False


def test_the_browser_leaving_full_screen_puts_the_board_back(page: Page, chapter: Chapter) -> None:
    page.goto("/board/")

    button = page.locator("button[data-fullscreen]")
    button.click()

    expect(button).to_have_attribute("aria-pressed", "true")

    page.evaluate("document.exitFullscreen()")  # as Esc or F11 does, outside the page's say

    expect(button).to_have_attribute("aria-pressed", "false")
    assert page.evaluate("document.elementFromPoint(700, 20).closest('header') !== null") is True


# --- a row of lanes is as tall as it is dragged ---------------------------------------------


def _cards_height(page: Page, faculty: Faculty) -> float:
    return page.locator(f"section [data-lane='{faculty.pk}']").bounding_box()["height"]


def test_dragging_a_lanes_edge_sizes_its_row(page: Page, chapter: Chapter) -> None:
    first, second, third = Faculty.objects.for_chapter(chapter.pk).order_by("name")

    page.goto("/board/")

    lanes = {
        f.pk: page.locator(f"section[data-key='{f.pk}']").bounding_box()
        for f in (first, second, third)
    }
    same_row = [f for f in (second, third) if abs(lanes[f.pk]["y"] - lanes[first.pk]["y"]) < 4]
    other_row = [f for f in (second, third) if f not in same_row]

    assert same_row  # the window is wide enough for two lanes beside each other

    before = {f.pk: _cards_height(page, f) for f in (first, second, third)}

    edge = page.locator(f"section[data-key='{first.pk}'] [data-lane-resize]").bounding_box()
    x, y = edge["x"] + edge["width"] / 2, edge["y"] + edge["height"] / 2

    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + 60, steps=6)
    page.mouse.up()

    taller = before[first.pk] + 60

    # the whole row follows, the other rows do not
    for faculty in (first, *same_row):
        assert abs(_cards_height(page, faculty) - taller) <= 2

    for faculty in other_row:
        assert abs(_cards_height(page, faculty) - before[faculty.pk]) <= 2

    page.reload()  # remembered

    assert abs(_cards_height(page, first) - taller) <= 2

    page.locator(f"section[data-key='{first.pk}'] [data-lane-resize]").dblclick()

    assert abs(_cards_height(page, first) - before[first.pk]) <= 2
    expect(page.locator(f"{MODAL} .card")).to_have_count(0)  # not the lane's own double click


# --- the sidebar ----------------------------------------------------------------------------


def test_on_a_wide_screen_the_sidebar_collapses_from_its_own_button(
    page: Page, chapter: Chapter
) -> None:
    page.goto("/hr/contracts/")

    sidebar = page.locator("nav[aria-label='main navigation']")

    expect(page.locator("header button[data-nav-toggle]")).to_be_hidden()
    assert sidebar.bounding_box()["width"] == 256

    sidebar.locator("button[data-nav-collapse]").click()

    expect(sidebar).to_have_css("width", "64px")

    sidebar.locator("button[data-nav-collapse]").click()

    expect(sidebar).to_have_css("width", "256px")


def test_on_a_small_screen_the_header_still_opens_the_sidebar(page: Page, chapter: Chapter) -> None:
    page.set_viewport_size({"width": 600, "height": 800})
    page.goto("/hr/contracts/")

    sidebar = page.locator("nav[aria-label='main navigation']")
    toggle = page.locator("header button[data-nav-toggle]")

    expect(sidebar).not_to_be_in_viewport()

    toggle.click()

    expect(sidebar).to_be_in_viewport()


def test_the_lock_switch_locks_the_contract_in_the_table(page: Page, chapter: Chapter) -> None:
    sami = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")

    page.goto("/hr/contracts/")

    switch = page.locator(ROWS).first.locator("td[data-col=is_locked] button[role=switch]")
    expect(switch).to_have_attribute("aria-checked", "false")

    switch.click()

    expect(
        page.locator(ROWS).first.locator("td[data-col=is_locked] button[role=switch]")
    ).to_have_attribute("aria-checked", "true")

    sami.refresh_from_db()
    assert sami.is_locked


def test_a_move_is_removed_and_put_back_before_applying(page: Page, chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")

    page.goto("/board/")
    page.evaluate(
        "window.htmx.ajax('GET', '/board/optimize/?strategy=maximize_students',"
        " {target: '#modal-container'})"
    )

    rows = page.locator(f"{MODAL} li[data-move]")
    row = page.locator(f"{MODAL} li[data-move='{karim.pk}']")

    expect(rows).to_have_count(5)
    expect(page.locator(f"{MODAL} li[data-move] select")).to_have_count(5)  # every row alike

    row.locator("button").click()

    expect(page.locator(f"{MODAL} li[data-removed]")).to_have_count(1)
    expect(row.locator("button")).to_be_focused()  # where the pointer was: undo is one press away
    expect(page.locator(f"{MODAL} h3")).to_contain_text("4 moves")

    page.keyboard.press("Enter")  # puts it back

    expect(page.locator(f"{MODAL} li[data-removed]")).to_have_count(0)

    row.locator("button").click()
    expect(page.locator(f"{MODAL} li[data-removed]")).to_have_count(1)

    page.locator(f"{MODAL} button[type=submit]").click()

    expect(page.locator(f"{MODAL} .card")).to_be_hidden()

    karim.refresh_from_db()
    assert karim.faculty is None
    assert (
        Contract.objects.get(chapter=chapter, employee__name="Dr. Hala").faculty.name == "Pharmacy"
    )


# --- what lines up ----------------------------------------------------------------------------


def test_the_reports_percentage_bars_are_on_one_line(page: Page, chapter: Chapter) -> None:
    faculty = Faculty.objects.get(chapter=chapter, name="Dentistry")

    page.goto(f"/reports/faculties/{faculty.pk}/staff/")

    rows = page.locator("[data-mix] > div")
    expect(rows).to_have_count(3)

    boxes = [rows.nth(index).bounding_box() for index in range(3)]

    assert len({round(box["y"]) for box in boxes}) == 1  # side by side, not stepped
    assert len({round(box["height"]) for box in boxes}) == 1
    assert boxes[0]["x"] < boxes[1]["x"] < boxes[2]["x"]


def test_a_cards_type_lines_up_with_its_terms_not_its_name(page: Page, chapter: Chapter) -> None:
    page.goto("/board/")

    def end_of(name: str) -> dict[str, float]:
        contract = Contract.objects.get(chapter=chapter, employee__name=name)
        card = page.locator(f".board-card[data-employee='{contract.employee_id}']")
        tag, terms = card.locator(".badge"), card.locator("[data-card-end] > span").last
        return {
            "tag": tag.bounding_box()["x"] + tag.bounding_box()["width"],
            "terms": terms.bounding_box()["x"],
            "name": card.locator("span").first.bounding_box()["width"],
        }

    # two names of different lengths, the same type and terms, in the same lane
    sami, lina = end_of("Dr. Sami"), end_of("Dr. Lina")

    assert sami["name"] != lina["name"]
    assert abs(sami["tag"] - lina["tag"]) < 1  # the tags are in a column
    assert 0 < sami["terms"] - sami["tag"] < 12  # right beside the terms


# --- a lane's own search ----------------------------------------------------------------------


def _shown(page: Page, faculty: Faculty | None) -> list[str]:
    key = faculty.pk if faculty else "unsigned"
    cards = page.locator(f"section [data-lane='{key}'] .board-card:visible > span:first-child")

    return [text.strip() for text in cards.all_inner_texts()]


def test_a_lanes_search_hides_the_cards_that_do_not_match(page: Page, chapter: Chapter) -> None:
    dentistry = Faculty.objects.get(chapter=chapter, name="Dentistry")
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    page.goto("/board/")

    lane = page.locator(f"section[data-key='{dentistry.pk}']")
    search = lane.locator("[data-lane-search] input")
    count = lane.locator("[data-lane-count]")

    expect(count).to_have_text("8")

    search.fill("bio")  # a specialization

    assert _shown(page, dentistry) == ["Dr. Hala", "Dr. Nour", "Dr. Ziad", "Dr. Maya"]
    expect(count).to_have_text("4 / 8")
    assert _shown(page, pharmacy) == ["Dr. Fadi", "Dr. Rana"]  # the other lanes are not searched

    search.fill("bio staff")  # every word, in any order

    assert _shown(page, dentistry) == ["Dr. Hala"]

    search.fill("sami")  # a name

    assert _shown(page, dentistry) == ["Dr. Sami"]

    # what is typed stays through a redraw of the board
    lane.locator(".board-card:visible").click(button="right")
    page.locator("#card-menu [data-switch=is_active]").click()

    expect(lane.locator(".board-card.excluded")).to_have_count(1)
    expect(lane.locator("[data-lane-search] input")).to_have_value("sami")
    assert _shown(page, dentistry) == ["Dr. Sami"]
    expect(lane.locator("[data-lane-count]")).to_have_text("1 / 8")

    lane.locator("[data-lane-search] input").press("Escape")

    expect(lane.locator("[data-lane-search] input")).to_have_value("")
    assert len(_shown(page, dentistry)) == 8
    expect(lane.locator("[data-lane-count]")).to_have_text("8")


def test_a_double_click_in_a_lanes_search_is_not_the_lanes(page: Page, chapter: Chapter) -> None:
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    page.goto("/board/")

    search = page.locator(f"section[data-key='{pharmacy.pk}'] [data-lane-search] input")
    search.fill("rana")
    search.dblclick()  # selects the word

    assert _shown(page, pharmacy) == ["Dr. Rana"]
    expect(page.locator(f"{MODAL} .card")).to_have_count(0)


def test_a_card_dragged_from_a_searched_lane_still_drops(page: Page, chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")  # unsigned
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    page.goto("/board/")
    page.locator("section [data-lane-search] input").first.fill("karim")

    assert _shown(page, None) == ["Dr. Karim"]

    card = page.locator(f".board-card[data-employee='{karim.employee_id}']")
    lane = page.locator(f"section [data-lane='{pharmacy.pk}']")
    start, end = card.bounding_box(), lane.bounding_box()

    page.mouse.move(start["x"] + 20, start["y"] + start["height"] / 2)
    page.mouse.down()
    page.mouse.move(end["x"] + 40, end["y"] + 30, steps=15)
    page.mouse.move(end["x"] + 45, end["y"] + 35, steps=5)
    page.mouse.up()

    expect(lane.locator(f".board-card[data-employee='{karim.employee_id}']")).to_have_count(1)
    assert _shown(page, None) == []  # the unsigned lane, still searched, holds no match now
