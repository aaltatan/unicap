"""The optimizer's moves: each can be made by any employee just like the one it names."""

import pytest
from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.exceptions import UserError
from unicap.app.models import Chapter, Contract, Faculty
from unicap.app.snapshot import Move, Optimization
from unicap.domain import Strategy

# the sample's Biology parttime PhDs, all three signed to Dentistry: alike in everything
TWINS = {"Dr. Nour", "Dr. Ziad", "Dr. Maya"}


def _contract(chapter: Chapter, name: str) -> Contract:
    return Contract.objects.get(chapter=chapter, employee__name=name)


@pytest.fixture
def optimization(chapter: Chapter) -> Optimization:
    return Chapter.objects.get_snapshot(chapter.pk).optimization(Strategy.MAXIMIZE_STUDENTS)


@pytest.fixture
def twin_move(optimization: Optimization) -> Move:
    """A move of one of the twins that leaves another twin where they are."""
    return next(m for m in optimization.moves if m.employee.name in TWINS and m.substitutes)


def test_a_move_offers_who_is_just_like_its_employee(
    optimization: Optimization, twin_move: Move
) -> None:
    moved = {move.employee.name for move in optimization.moves}

    names = {substitute.employee.name for substitute in twin_move.substitutes}

    assert names
    assert names <= TWINS - moved  # alike, and not moved themselves
    assert optimization.has_substitutes


def test_a_move_of_someone_unlike_any_other_offers_no_one(optimization: Optimization) -> None:
    hala = next(move for move in optimization.moves if move.employee.name == "Dr. Hala")

    # the other fulltime staff PhD of Biology, Dr. Rana, is signed to another faculty
    assert hala.substitutes == ()


def test_every_move_names_who_makes_it_in_a_select(
    admin_client: Client, chapter: Chapter, optimization: Optimization
) -> None:
    response = admin_client.get(
        reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx()
    )

    html = HTMLParser(response.content)

    for move in optimization.moves:
        # the same row whoever could make the move: one option when no one else could
        select = html.css_first(f"select[name='substitute-{move.contract_id}']")

        options = select.css("option")

        assert options[0].attributes["value"] == str(move.contract_id)
        assert "selected" in options[0].attributes
        assert [option.text(strip=True) for option in options] == [
            move.employee.name,
            *(substitute.employee.name for substitute in move.substitutes),
        ]


def test_applying_with_a_substitute_moves_them_instead(
    admin_client: Client, chapter: Chapter, twin_move: Move
) -> None:
    substitute = twin_move.substitutes[0]

    preview = admin_client.get(
        reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx()
    )
    placements = HTMLParser(preview.content).css_first("input[name=placements]")

    admin_client.post(
        reverse("board:optimize"),
        {
            "placements": placements.attributes["value"],
            f"substitute-{twin_move.contract_id}": substitute.contract_id,
        },
        **htmx(),
    )

    stayed = Contract.objects.get(pk=twin_move.contract_id)
    moved = Contract.objects.get(pk=substitute.contract_id)
    target = Faculty.objects.get(chapter=chapter, name=twin_move.after.name)  # type: ignore[union-attr]

    assert stayed.faculty.name == twin_move.before.name  # type: ignore[union-attr]
    assert moved.faculty == target


def test_a_substitute_gives_the_same_numbers(
    chapter: Chapter, optimization: Optimization, twin_move: Move
) -> None:
    substitutes = {twin_move.contract_id: twin_move.substitutes[0].contract_id}

    Chapter.objects.apply_placements(chapter, optimization.placements, substitutes=substitutes)

    report = Chapter.objects.get_snapshot(chapter.pk).report()

    assert report.capacity == optimization.after.capacity
    assert len(report.violations) == len(optimization.after.violations)


def test_choosing_the_employee_themselves_changes_nothing(
    chapter: Chapter, optimization: Optimization, twin_move: Move
) -> None:
    snapshot = Chapter.objects.get_snapshot(chapter.pk)

    same = snapshot.substituted(
        optimization.placements, {twin_move.contract_id: twin_move.contract_id}
    )

    assert same == optimization.placements


def test_a_substitute_must_be_one_of_the_moves(
    chapter: Chapter, optimization: Optimization, twin_move: Move
) -> None:
    snapshot = Chapter.objects.get_snapshot(chapter.pk)

    unlike = _contract(chapter, "Dr. Sami").pk  # fulltime staff, of Dentistry
    moving = next(
        m.contract_id for m in optimization.moves if m.contract_id != twin_move.contract_id
    )

    for wrong in (unlike, moving, 999_999):
        with pytest.raises(UserError, match="choose another employee"):
            snapshot.substituted(optimization.placements, {twin_move.contract_id: wrong})

    with pytest.raises(UserError):
        snapshot.substituted(optimization.placements, {999_999: twin_move.contract_id})


def test_a_refused_substitute_moves_nothing(
    admin_client: Client, chapter: Chapter, optimization: Optimization, twin_move: Move
) -> None:
    before = dict(Contract.objects.for_chapter(chapter.pk).values_list("pk", "faculty_id"))

    response = admin_client.post(
        reverse("board:optimize"),
        {
            "placements": HTMLParser(
                admin_client.get(
                    reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx()
                ).content
            )
            .css_first("input[name=placements]")
            .attributes["value"],
            f"substitute-{twin_move.contract_id}": _contract(chapter, "Dr. Sami").pk,
        },
        **htmx(),
    )

    assert response.status_code == 200
    assert dict(Contract.objects.for_chapter(chapter.pk).values_list("pk", "faculty_id")) == before


def test_a_locked_twin_is_not_offered(chapter: Chapter, twin_move: Move) -> None:
    substitute = twin_move.substitutes[0]

    Contract.objects.filter(pk=substitute.contract_id).update(is_locked=True)

    again = Chapter.objects.get_snapshot(chapter.pk).optimization(Strategy.MAXIMIZE_STUDENTS)

    offered = {s.contract_id for move in again.moves for s in move.substitutes}

    assert substitute.contract_id not in offered


# --- removing moves ---------------------------------------------------------------------


def _preview(client: Client) -> HTMLParser:
    response = client.get(reverse("board:optimize"), {"strategy": "maximize_students"}, **htmx())

    return HTMLParser(response.content)


def _form(html: HTMLParser) -> dict[str, object]:
    """What the modal's form posts: its hidden values, its selects and the moves removed."""
    data: dict[str, object] = {
        node.attributes["name"]: node.attributes["value"]
        for node in html.css("input[type=hidden]:not([name=removed])")
    }
    data["removed"] = [node.attributes["value"] for node in html.css("input[name=removed]")]

    for select in html.css("select"):
        chosen = select.css_first("option[selected]") or select.css_first("option")
        data[select.attributes["name"]] = chosen.attributes["value"]

    return data


def test_every_move_has_its_remove_button(
    admin_client: Client, chapter: Chapter, optimization: Optimization
) -> None:
    html = _preview(admin_client)

    rows = html.css("li[data-move]")

    assert [row.attributes["data-move"] for row in rows] == [
        str(move.contract_id) for move in optimization.moves
    ]

    for row in rows:
        button = row.css_first("button[hx-post]")

        assert button.attributes["hx-vals"] == f'{{"remove": "{row.attributes["data-move"]}"}}'
        assert button.attributes["hx-target"] == "#modal-container"
        assert len(row.css("select")) == 1


def test_removing_a_move_redraws_the_preview_without_it(
    admin_client: Client, chapter: Chapter, optimization: Optimization
) -> None:
    karim = _contract(chapter, "Dr. Karim")  # unsigned: the optimizer signs him to Pharmacy
    form = _form(_preview(admin_client))

    response = admin_client.post(reverse("board:optimize"), {**form, "remove": karim.pk}, **htmx())

    html = HTMLParser(response.content)
    row = html.css_first(f"li[data-move='{karim.pk}']")
    reviewed = response.context["optimization"]

    assert "HX-Trigger" not in response  # drawn again: nothing applied, nothing closed
    assert "data-removed" in row.attributes
    assert row.css_first("input[name=removed]").attributes["value"] == str(karim.pk)
    # its button now puts it back, and is where the focus goes
    assert row.css_first("button").attributes["hx-vals"] == f'{{"restore": "{karim.pk}"}}'
    assert "autofocus" in row.css_first("button").attributes
    assert (reviewed.kept, reviewed.removed) == (len(optimization.moves) - 1, 1)
    # the figures are those of the moves kept
    assert reviewed.after.capacity < optimization.after.capacity
    assert reviewed.after_outcome.moves == reviewed.kept

    karim.refresh_from_db()
    assert karim.faculty is None  # nothing is saved


def test_a_removed_move_can_be_put_back(
    admin_client: Client, chapter: Chapter, optimization: Optimization
) -> None:
    karim = _contract(chapter, "Dr. Karim")
    url = reverse("board:optimize")

    removed = admin_client.post(
        url, {**_form(_preview(admin_client)), "remove": karim.pk}, **htmx()
    )
    form = _form(HTMLParser(removed.content))

    assert form["removed"] == [str(karim.pk)]

    restored = admin_client.post(url, {**form, "restore": karim.pk}, **htmx())

    reviewed = restored.context["optimization"]

    assert reviewed.removed == 0
    assert reviewed.after.capacity == optimization.after.capacity
    assert not HTMLParser(restored.content).css("[data-removed]")


def test_applying_leaves_the_removed_moves_out(
    admin_client: Client, chapter: Chapter, optimization: Optimization
) -> None:
    karim = _contract(chapter, "Dr. Karim")
    url = reverse("board:optimize")

    removed = admin_client.post(
        url, {**_form(_preview(admin_client)), "remove": karim.pk}, **htmx()
    )

    response = admin_client.post(url, _form(HTMLParser(removed.content)), **htmx())

    assert "close-modal" in response["HX-Trigger"]

    karim.refresh_from_db()
    assert karim.faculty is None

    for move in optimization.moves:
        if move.contract_id != karim.pk:
            contract = Contract.objects.get(pk=move.contract_id)
            assert (contract.faculty.name if contract.faculty else None) == (
                move.after.name if move.after else None
            )


def test_with_every_move_removed_nothing_can_be_applied(
    admin_client: Client, chapter: Chapter, optimization: Optimization
) -> None:
    url = reverse("board:optimize")
    form = _form(_preview(admin_client))
    form["removed"] = [str(move.contract_id) for move in optimization.moves[1:]]

    response = admin_client.post(
        url, {**form, "remove": optimization.moves[0].contract_id}, **htmx()
    )

    html = HTMLParser(response.content)
    reviewed = response.context["optimization"]

    assert reviewed.kept == 0
    assert reviewed.after.capacity == reviewed.before.capacity
    assert "disabled" in html.css_first("button[type=submit]").attributes


def test_a_removed_moves_substitute_is_kept_for_when_it_comes_back(
    admin_client: Client, chapter: Chapter, twin_move: Move
) -> None:
    substitute = twin_move.substitutes[0]
    form = _form(_preview(admin_client))
    form[f"substitute-{twin_move.contract_id}"] = substitute.contract_id

    response = admin_client.post(
        reverse("board:optimize"), {**form, "remove": twin_move.contract_id}, **htmx()
    )

    select = HTMLParser(response.content).css_first(
        f"select[name='substitute-{twin_move.contract_id}']"
    )

    assert select.css_first("option[selected]").attributes["value"] == str(substitute.contract_id)


def test_review_refuses_a_faculty_that_is_not_the_chapters(chapter: Chapter) -> None:
    snapshot = Chapter.objects.get_snapshot(chapter.pk)
    karim = _contract(chapter, "Dr. Karim")

    with pytest.raises(UserError, match="not in the chapter"):
        snapshot.review(Strategy.MAXIMIZE_STUDENTS, {karim.pk: 999_999})


def test_a_viewer_cannot_trim_or_apply(viewer_client: Client, chapter: Chapter) -> None:
    response = viewer_client.post(reverse("board:optimize"), {"remove": 1}, **htmx())

    assert response.status_code == 403
