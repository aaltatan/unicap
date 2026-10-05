"""The board: drops, previews, switches, reset and the optimizer."""

import json

import pytest
from django.test import Client
from django.urls import reverse
from pytest_mock import MockerFixture
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app import snapshot
from unicap.app.models import AppSettings, Chapter, Contract, Faculty
from unicap.domain import Strategy


def _lane_names(content: bytes) -> dict[str, list[str]]:
    html = HTMLParser(content)
    return {
        lane.attributes["data-lane"]: [
            card.css_first("span").text(strip=True) for card in lane.css(".board-card")
        ]
        for lane in html.css("[data-lane]")
    }


def test_board_page_has_every_lane(admin_client: Client, chapter: Chapter) -> None:
    lanes = _lane_names(admin_client.get(reverse("board:index")).content)

    assert lanes["unsigned"] == ["Dr. Karim", "Ola"]
    assert len(lanes) == 4


def test_refresh_gets_only_the_board(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(reverse("board:index"), **htmx("board"))

    html = HTMLParser(response.content)
    assert html.css_first("#board") is not None
    assert html.css_first("nav[aria-label]") is None


def test_drop_moves_the_card(admin_client: Client, chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")

    response = admin_client.post(
        reverse("board:move"),
        {"employee": karim.employee_id, "faculty": pharmacy.pk},
        **htmx("board"),
    )

    lanes = _lane_names(response.content)
    assert "Dr. Karim" in lanes[str(pharmacy.pk)]
    assert "Dr. Karim" not in lanes["unsigned"]

    card = HTMLParser(response.content).css_first(f"[data-employee='{karim.employee_id}']")
    assert "counted" in card.attributes["class"].split()


def test_drop_back_to_unsigned(admin_client: Client, chapter: Chapter) -> None:
    sami = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")

    admin_client.post(
        reverse("board:move"), {"employee": sami.employee_id, "faculty": ""}, **htmx()
    )

    sami.refresh_from_db()
    assert sami.faculty is None


def test_preview_says_what_each_lane_would_give(admin_client: Client, chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    dentistry = Faculty.objects.get(chapter=chapter, name="Dentistry")

    lanes = admin_client.get(reverse("board:preview"), {"employee": karim.employee_id}).json()[
        "lanes"
    ]

    assert lanes["unsigned"]["counted"] is None
    assert lanes[str(pharmacy.pk)] | {"hint": ""} == {
        "counted": True,
        "status": "counted",
        "capacity": 170,
        "hint": "",
    }
    assert lanes[str(dentistry.pk)]["counted"] is False


def test_double_click_switches_the_contract(admin_client: Client, chapter: Chapter) -> None:
    sami = Contract.objects.get(chapter=chapter, employee__name="Dr. Sami")

    response = admin_client.post(reverse("board:toggle"), {"employee": sami.employee_id}, **htmx())

    sami.refresh_from_db()
    assert not sami.is_active
    card = HTMLParser(response.content).css_first(f"[data-employee='{sami.employee_id}']")
    assert "excluded" in card.attributes["class"].split()


def test_reset(admin_client: Client, chapter: Chapter) -> None:
    confirm = admin_client.get(reverse("board:reset"), **htmx())
    assert b"14" in confirm.content

    response = admin_client.post(reverse("board:reset"), **htmx())

    assert json.loads(response["HX-Trigger"]) == {"refresh": True, "close-modal": True}
    assert not Contract.objects.for_chapter(chapter.pk).signed().exists()


def test_optimize_previews_then_applies(admin_client: Client, chapter: Chapter) -> None:
    preview = admin_client.get(
        reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx()
    )

    html = HTMLParser(preview.content)
    placements = html.css_first("input[name=placements]").attributes["value"]
    assert json.loads(placements)

    admin_client.post(reverse("board:optimize"), {"placements": placements}, **htmx())

    report = Chapter.objects.get_snapshot(chapter.pk).report()
    assert report.capacity > 155
    assert report.is_compliant


def test_every_strategy_previews(admin_client: Client, chapter: Chapter) -> None:
    for strategy in ("minimize_changes", "less_salaries", "best_staff_percentage"):
        response = admin_client.get(reverse("board:optimize"), {"strategy": strategy}, **htmx())

        assert response.status_code == 200


def test_the_optimizer_runs_the_settings_rounds(
    admin_client: Client, chapter: Chapter, mocker: MockerFixture
) -> None:
    settings = AppSettings.get_solo()
    settings.optimizer_rounds = 3
    settings.save()

    spy = mocker.spy(snapshot, "optimize")

    admin_client.get(reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx())

    assert spy.call_args.args[2] == 3


def test_recommend_opens_its_form(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(reverse("board:recommend"), **htmx())

    html = HTMLParser(response.content)

    assert response.status_code == 200
    assert html.css_first("select[name=strategy]")
    assert len(html.css("input[name=kinds]")) == 4
    assert not html.css("tbody td")  # nothing recommended before asking


def test_recommend_lists_the_contracts_to_sign(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(
        reverse("board:recommend"),
        {"strategy": "fewest_contracts", "kinds": ["fulltime_staff", "fulltime_borrowed"]},
        **htmx(),
    )

    html = HTMLParser(response.content)
    kinds = {row.css("td")[2].text(strip=True) for row in html.css("table")[1].css("tbody tr")}

    assert response.status_code == 200
    assert kinds <= {"fulltime staff PhD", "fulltime borrowed PhD"}
    assert Contract.objects.filter(chapter=chapter).count() == 16  # nothing saved


def test_a_viewer_may_ask_for_recommendations(viewer_client: Client, chapter: Chapter) -> None:
    response = viewer_client.get(
        reverse("board:recommend"), {"strategy": "low_salaries", "kinds": ["master"]}, **htmx()
    )

    assert response.status_code == 200


def test_the_report_compares_students_with_the_capacity(
    admin_client: Client, chapter: Chapter
) -> None:
    html = HTMLParser(admin_client.get(reverse("reports:capacity")).content)

    headers = [th.text(strip=True) for th in html.css("thead th")]
    footer = [td.text(strip=True) for td in html.css("tfoot td")]

    computer_science = [td.text(strip=True) for td in html.css("tbody tr")[0].css("td")]

    start = headers.index("capacity")
    assert headers[start : start + 4] == [
        "capacity",
        "current students",
        "max students",
        "free seats",
    ]
    assert computer_science[start : start + 4] == ["75", "60", "200", "15"]
    # chapter: capacity, students now (summed), the faculties' max (no chapter max), free
    assert footer[1:5] == ["155", "120", "400", "35"]


def test_the_dashboard_draws_how_each_faculty_is_filled(
    admin_client: Client, chapter: Chapter
) -> None:
    html = HTMLParser(admin_client.get(reverse("board:dashboard")).content)

    charts = {
        node.attributes["id"]: json.loads(node.text())
        for node in html.css("script[id^=composition-]")
    }
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    data = charts[f"composition-{pharmacy.pk}"]

    assert data["total"] == sum(item["count"] for item in data["slices"])
    assert data["total"] == sum(group["count"] for group in data["groups"])
    assert [group["employment"] for group in data["groups"]] == sorted(
        {group["employment"] for group in data["groups"]}, key=["staff", "borrowed"].index
    )
    assert len(html.css("[x-data^=compositionChart]")) == len(charts) == 3


def test_cards_are_in_staff_order(admin_client: Client, chapter: Chapter) -> None:
    """The faculty lanes' order is the domain's (test_ordering); here, the page uses it."""
    # Dr. Karim (a PhD) signed after Ola (a master)
    Contract.objects.filter(chapter=chapter, employee__name="Dr. Karim").update(position=10_000)

    lanes = _lane_names(admin_client.get(reverse("board:index")).content)

    assert lanes["unsigned"] == ["Dr. Karim", "Ola"]  # PhD before master, whatever the signing


def test_the_charts_leave_masters_out(admin_client: Client, chapter: Chapter) -> None:
    html = HTMLParser(admin_client.get(reverse("board:dashboard")).content)

    kinds = {
        item["kind"]
        for node in html.css("script[id^=composition-]")
        for item in json.loads(node.text())["slices"]
    }

    assert kinds
    assert "master" not in kinds


def test_each_move_tells_the_teachers_specialization_and_type(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    Contract.objects.filter(chapter=chapter).update(faculty=None)  # so the optimizer signs them
    optimization = Chapter.objects.get_snapshot(chapter.pk).optimization(Strategy.MAXIMIZE_STUDENTS)

    response = admin_client.get(
        reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx()
    )
    items = HTMLParser(response.content).css("ul li")

    assert len(items) == len(optimization.moves) > 0

    for item, move in zip(items, optimization.moves, strict=True):
        text = item.text()
        kind = move.after.type_of(move.employee.specialization)  # in the faculty it moves to

        assert move.employee.name in text
        assert move.employee.specialization.name in text
        assert item.css_first(".badge").text(strip=True) == kind.value


# --- input that is not what the page sends ------------------------------------------------


def test_an_unknown_strategy_previews_the_default_one(
    admin_client: Client, chapter: Chapter
) -> None:
    response = admin_client.get(reverse("board:optimize"), {"strategy": "no-such"}, **htmx())

    assert response.status_code == 200
    assert HTMLParser(response.content).css_first("input[name=placements]") is not None


@pytest.mark.parametrize("placements", ["[1, 2]", "null", "{", '{"%(contract)s": "x"}', "7"])
def test_placements_that_cannot_be_read_move_nothing(
    admin_client: Client, chapter: Chapter, placements: str
) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")

    response = admin_client.post(
        reverse("board:optimize"), {"placements": placements % {"contract": karim.pk}}, **htmx()
    )

    assert response.status_code == 200
    karim.refresh_from_db()
    assert karim.faculty is None


def test_placements_on_a_faculty_that_is_not_the_chapters_move_nothing(
    admin_client: Client, chapter: Chapter
) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")
    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    elsewhere = Faculty.objects.create(
        chapter=Chapter.objects.create(name="other"), name="Elsewhere", students_per_phd=10
    )

    for faculty_id in (elsewhere.pk, 999_999):
        response = admin_client.post(
            reverse("board:optimize"),
            {"placements": json.dumps({karim.pk: faculty_id})},
            **htmx(),
        )

        assert response.status_code == 200
        karim.refresh_from_db()
        assert karim.faculty is None

    admin_client.post(reverse("board:move"), {"employee": karim.employee_id, "faculty": 999_999})
    karim.refresh_from_db()
    assert karim.faculty is None

    admin_client.post(
        reverse("board:move"), {"employee": karim.employee_id, "faculty": pharmacy.pk}
    )
    karim.refresh_from_db()
    assert karim.faculty == pharmacy


# --- a chapter whose stored rows break a rule ----------------------------------------------


@pytest.fixture
def broken(chapter: Chapter) -> Chapter:
    """The sample chapter, with a max the faculties cannot hold (saved behind the rules)."""
    Chapter.objects.filter(pk=chapter.pk).update(max_students=10_000)
    return chapter


@pytest.mark.parametrize(
    "url_name",
    ["board:index", "hr:contracts:index", "hr:employees:index", "edu:faculties:index"],
)
def test_a_broken_chapter_shows_its_problem_instead_of_the_page(
    admin_client: Client, broken: Chapter, url_name: str
) -> None:
    response = admin_client.get(reverse(url_name))

    assert response.status_code == 409
    assert "cannot exceed" in HTMLParser(response.content).css_first("main").text()


def test_a_broken_chapter_is_a_toast_on_an_htmx_request(
    admin_client: Client, broken: Chapter
) -> None:
    response = admin_client.get(reverse("board:optimize"), **htmx())

    assert response.status_code == 200
    assert response["HX-Reswap"] == "none"
    assert "cannot exceed" in response.content.decode()


def test_a_broken_chapter_can_still_be_fixed(admin_client: Client, broken: Chapter) -> None:
    response = admin_client.post(
        reverse("chapters:update", kwargs={"pk": broken.pk}),
        {"name": broken.name, "max_students": ""},
        **htmx(),
    )

    assert "close-modal" in response["HX-Trigger"]
    assert admin_client.get(reverse("board:index")).status_code == 200
