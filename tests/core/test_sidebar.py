"""The sidebar: each table's link has a "new" button for those who may add."""

from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from unicap.app.models import Chapter

CREATE_URLS = [
    "hr:contracts:create",
    "hr:employees:create",
    "edu:faculties:create",
    "edu:specializations:create",
    "chapters:create",
]


def new_buttons(client: Client) -> list[str]:
    """The forms the sidebar's "new" buttons open, in the sidebar's order."""
    tree = HTMLParser(client.get(reverse("board:dashboard")).content)

    return [button.attributes["hx-get"] for button in tree.css("nav li button[hx-get]")]


def test_each_table_link_has_a_new_button(admin_client: Client, chapter: Chapter) -> None:
    assert new_buttons(admin_client) == [reverse(name) for name in CREATE_URLS]


def test_the_new_buttons_open_the_form_in_the_modal(admin_client: Client, chapter: Chapter) -> None:
    tree = HTMLParser(admin_client.get(reverse("board:dashboard")).content)

    targets = {button.attributes["hx-target"] for button in tree.css("nav li button[hx-get]")}

    assert targets == {"#modal-container"}


def test_a_viewer_gets_no_new_button(viewer_client: Client, chapter: Chapter) -> None:
    assert new_buttons(viewer_client) == []
