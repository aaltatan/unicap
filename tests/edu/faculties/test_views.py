"""The faculty form: its accepted specializations are a formset edited in place."""

from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.models import Chapter, Faculty


def form_data(client: Client, url: str) -> dict[str, str]:
    """The form's fields as the browser would post them, untouched."""
    html = HTMLParser(client.get(url, **htmx()).content)
    data: dict[str, str] = {}

    for field in html.css("form input[name], form select[name], form textarea[name]"):
        name = field.attributes["name"]
        kind = field.attributes.get("type")

        if "__prefix__" in name:  # the <template> row new rows are copied from
            continue

        if kind == "checkbox":
            if "checked" in field.attributes:
                data[name] = "on"
        elif field.tag == "select":
            selected = field.css_first("option[selected]")
            data[name] = (selected.attributes.get("value") or "") if selected else ""
        elif field.tag == "textarea":
            data[name] = field.text()
        else:
            data[name] = field.attributes.get("value") or ""

    return data


def test_a_new_row_removed_before_saving_needs_nothing_filled(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).first()
    shares = faculty.shares.count()
    url = reverse("edu:faculties:update", args=(faculty.pk,))

    data = form_data(admin_client, url)
    index = int(data["shares-TOTAL_FORMS"])
    data["shares-TOTAL_FORMS"] = str(index + 1)
    data |= {  # added, left empty, then removed: marked DELETE
        f"shares-{index}-specialization": "",
        f"shares-{index}-specialization_type": "specialized",
        f"shares-{index}-DELETE": "on",
    }

    response = admin_client.post(url, data, **htmx())

    assert "HX-Trigger" in response  # saved: the modal closes and the table refreshes
    assert faculty.shares.count() == shares
