"""Import samples: a file of dummy rows to fill in, with dropdowns in Excel."""

import csv
import io
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.choices import ContractTypeChoices, DegreeChoices
from unicap.app.models import Chapter
from unicap.app.resources import ContractResource, EmployeeResource, sample_file

IMPORTS = ["edu:faculties:import", "edu:specializations:import", "hr:employees:import"]
ALL_IMPORTS = [*IMPORTS, "hr:contracts:import"]


def dropdowns(sheet: Worksheet) -> dict[str, list[str]]:
    """Each column's dropdown values, by its header."""
    lists = sheet.parent["lists"]
    found = {}

    for validation in sheet.data_validations.dataValidation:
        column = str(validation.sqref).split(":")[0].rstrip("0123456789")
        cells = lists[validation.formula1.split("!")[1].replace("$", "")]
        found[sheet[f"{column}1"].value] = [cell.value for [cell] in cells]

    return found


@pytest.mark.parametrize("url_name", ALL_IMPORTS)
def test_the_import_modal_offers_both_samples(
    admin_client: Client,
    chapter: Chapter,
    url_name: str,
) -> None:
    response = admin_client.get(reverse(url_name), **htmx())

    links = [a.attributes["href"] for a in HTMLParser(response.content).css("a[download]")]

    assert links == [f"{reverse(url_name)}?sample=xlsx", f"{reverse(url_name)}?sample=csv"]


@pytest.mark.parametrize("url_name", ALL_IMPORTS)
@pytest.mark.parametrize("extension", ["xlsx", "csv"])
def test_a_sample_is_a_file_to_save(
    admin_client: Client,
    chapter: Chapter,
    url_name: str,
    extension: str,
) -> None:
    response = admin_client.get(reverse(url_name), {"sample": extension})

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    assert f".{extension}" in response["Content-Disposition"]


def test_a_sample_needs_the_right_to_import(client: Client, chapter: Chapter) -> None:
    response = client.get(reverse("hr:employees:import"), {"sample": "xlsx"})

    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_a_sample_holds_the_exports_headers_and_dummy_rows(chapter: Chapter) -> None:
    content = sample_file(EmployeeResource(chapter=chapter), "csv")

    assert content.startswith("﻿".encode())  # Excel reads it as UTF-8

    [headers, *rows] = csv.reader(io.StringIO(content.decode("utf-8-sig")))

    assert headers == ["name", "specialization", "is active", "cannot be counted in", "notes"]
    assert [row[0] for row in rows] == ["employee 1", "employee 2"]
    assert {row[1] for row in rows} <= set(chapter.specializations.values_list("name", flat=True))


@pytest.mark.django_db
def test_an_excel_sample_has_a_dropdown_on_each_listed_column(chapter: Chapter) -> None:
    book = load_workbook(io.BytesIO(sample_file(ContractResource(chapter=chapter), "xlsx")))

    assert book["lists"].sheet_state == "hidden"

    found = dropdowns(book.active)

    assert found["employee"] == sorted(chapter.employees.values_list("name", flat=True))
    assert found["faculty"] == sorted(chapter.faculties.values_list("name", flat=True))
    assert found["degree"] == [str(label) for label in DegreeChoices.labels]
    assert found["contract type"] == [str(label) for label in ContractTypeChoices.labels]
    assert found["is active"] == ["yes", "no"]
    assert "notes" not in found


@pytest.mark.parametrize("url_name", IMPORTS)
@pytest.mark.parametrize("extension", ["xlsx", "csv"])
def test_a_sample_imports_as_it_is(
    admin_client: Client,
    chapter: Chapter,
    url_name: str,
    extension: str,
) -> None:
    content = admin_client.get(reverse(url_name), {"sample": extension}).content
    upload = SimpleUploadedFile(f"sample.{extension}", content)

    response = admin_client.post(reverse(url_name), {"file": upload}, **htmx())

    assert json.loads(response["HX-Trigger"])["refresh"] is True
