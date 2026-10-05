"""Exports: in the user's language, of the rows on screen; imports read any language."""

import csv
import io
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import translation
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.choices import ContractTypeChoices
from unicap.app.models import Chapter, Contract, Employee, Faculty

ARABIC = {"HTTP_ACCEPT_LANGUAGE": "ar"}


def export_rows(client: Client, url_name: str, **params: str) -> list[list[str]]:
    response = client.get(reverse(url_name), {"export": "csv", **params})
    text = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def arabic(text: object) -> str:
    """`text` in Arabic: a lazy label, or a msgid."""
    with translation.override("ar"):
        return translation.gettext(text) if isinstance(text, str) else str(text)


def test_headers_are_the_columns_names(admin_client: Client, chapter: Chapter) -> None:
    [headers, *_rows] = export_rows(admin_client, "edu:faculties:index")

    assert headers[:2] == ["name", "students per PhD"]
    assert "specialized" in headers
    assert "students_per_phd" not in headers


def test_an_arabic_export_translates_headers_choices_and_booleans(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    response = admin_client.get(reverse("hr:contracts:index"), {"export": "csv"}, **ARABIC)

    assert response.content.startswith("﻿".encode())  # Excel reads it as UTF-8

    [headers, *rows] = csv.reader(io.StringIO(response.content.decode("utf-8-sig")))

    contract_type = Contract._meta.get_field("contract_type")  # noqa: SLF001
    assert arabic(contract_type.verbose_name) in headers

    column = headers.index(arabic(contract_type.verbose_name))
    assert {row[column] for row in rows} <= {
        arabic(ContractTypeChoices.FULLTIME.label),
        arabic(ContractTypeChoices.PARTTIME.label),
    }

    active = headers.index(arabic(Contract._meta.get_field("is_active").verbose_name))  # noqa: SLF001
    assert {row[active] for row in rows} <= {arabic("yes"), arabic("no")}


def test_the_file_is_named_after_the_page(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(reverse("edu:faculties:index"), {"export": "xlsx"}, **ARABIC)

    assert "filename*=utf-8''" in response["Content-Disposition"]  # an Arabic name, encoded


def test_an_export_holds_the_filtered_rows_only(admin_client: Client, chapter: Chapter) -> None:
    [_headers, *rows] = export_rows(admin_client, "edu:faculties:index", q="Dentistry")

    assert [row[0] for row in rows] == ["Dentistry"]


def test_an_arabic_export_imports_back(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(reverse("hr:employees:index"), {"export": "csv"}, **ARABIC)
    [headers, *rows] = csv.reader(io.StringIO(response.content.decode("utf-8-sig")))

    name = headers.index(arabic(Employee._meta.get_field("name").verbose_name))  # noqa: SLF001
    notes = headers.index(arabic(Employee._meta.get_field("notes").verbose_name))  # noqa: SLF001
    rows[0][notes] = "imported from Arabic"

    output = io.StringIO()
    csv.writer(output).writerows([headers, *rows])
    upload = SimpleUploadedFile("employees.csv", output.getvalue().encode("utf-8-sig"))

    response = admin_client.post(reverse("hr:employees:import"), {"file": upload}, **htmx())

    assert json.loads(response["HX-Trigger"])["refresh"] is True
    assert chapter.employees.get(name=rows[0][name]).notes == "imported from Arabic"
    assert chapter.employees.count() == len(rows)


@pytest.mark.parametrize("value", ["yes", "no", "1", "0", "True"])
def test_imports_read_yes_no_in_any_language(
    admin_client: Client,
    chapter: Chapter,
    value: str,
) -> None:
    yes = value in ("yes", "1", "True")
    content = f"{arabic('name')},specialization,is_active\nDr. New,Biology,{arabic(value)}\n"
    upload = SimpleUploadedFile("employees.csv", content.encode())

    admin_client.post(reverse("hr:employees:import"), {"file": upload}, **htmx())

    assert chapter.employees.get(name="Dr. New").is_active is yes


def test_a_facultys_reports_are_in_the_reports_section_not_its_table_row(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    faculty = Faculty.objects.for_chapter(chapter.pk).first()
    staff = reverse("reports:staff", args=(faculty.pk,))
    pivot = reverse("reports:staff-pivot", args=(faculty.pk,))

    table = HTMLParser(admin_client.get(reverse("edu:faculties:index")).content)
    reports = HTMLParser(admin_client.get(reverse("reports:faculties")).content)

    assert table.css_first(f"#table a[href='{staff}']") is None
    assert reports.css_first(f"a[href='{staff}']")
    assert reports.css_first(f"a[href='{pivot}']")
