"""The pivot reports (small specialized / supported tables) and every report as a PDF."""

import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse
from docx import Document
from pytest_django.fixtures import Settings
from pytest_mock import MockerFixture
from selectolax.parser import HTMLParser

from unicap.app.choices import ReportChoices
from unicap.app.models import Chapter, Faculty
from unicap.app.reports import PdfError, documents, pdf, to_pdf
from unicap.app.reports.docx import DOCX_CONTENT_TYPE
from unicap.app.reports.pdf import PDF_CONTENT_TYPE

PDF = b"%PDF-1.7 converted"


@pytest.fixture(autouse=True)
def media(settings: Settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def faculty(chapter: Chapter) -> Faculty:
    """A faculty of the sample chapter with contracts signed to it."""
    return Faculty.objects.for_chapter(chapter.pk).filter(contracts__isnull=False).first()


@pytest.fixture
def converter(mocker: MockerFixture) -> list[bytes]:
    """An office suite that writes a PDF; holds the .docx files it was given."""
    received: list[bytes] = []

    def convert(source: Path, target: Path) -> None:
        received.append(source.read_bytes())
        target.write_bytes(PDF)

    mocker.patch.object(pdf, "_converter", return_value=convert)

    return received


def docx_text(content: bytes) -> str:
    document = Document(BytesIO(content))
    cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return "\n".join([*(p.text for p in document.paragraphs), *cells])


def split(cell: str) -> tuple[int, int]:
    """A pivot cell as (counted, signed): `3` or `3 / 5`."""
    counted, _slash, signed = cell.partition(" / ")
    return int(counted), int(signed or counted)


# --- pdf ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url_name",
    ["reports:capacity-pdf", "reports:capacity-pivot-pdf"],
)
def test_a_chapter_report_downloads_as_pdf(
    admin_client: Client,
    chapter: Chapter,
    converter: list[bytes],
    url_name: str,
) -> None:
    response = admin_client.get(reverse(url_name))

    assert response.status_code == 200
    assert response["Content-Type"] == PDF_CONTENT_TYPE
    assert ".pdf" in response["Content-Disposition"]
    assert b"".join(response.streaming_content) == PDF
    assert chapter.name in docx_text(converter[0])  # the filled Word report was converted


@pytest.mark.parametrize("url_name", ["reports:staff-pdf", "reports:staff-pivot-pdf"])
def test_a_faculty_report_downloads_as_pdf(
    admin_client: Client,
    faculty: Faculty,
    converter: list[bytes],
    url_name: str,
) -> None:
    response = admin_client.get(reverse(url_name, args=(faculty.pk,)))

    assert response["Content-Type"] == PDF_CONTENT_TYPE
    assert b"".join(response.streaming_content) == PDF
    assert faculty.name in docx_text(converter[0])


def test_without_an_office_suite_the_page_says_why(
    admin_client: Client,
    chapter: Chapter,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(pdf, "soffice_path", return_value=None)
    mocker.patch.object(pdf.shutil, "which", return_value=None)

    response = admin_client.get(reverse("reports:capacity-pdf"), follow=True)

    assert response.redirect_chain[0][0] == reverse("reports:capacity")
    assert "LibreOffice" in response.content.decode()


def test_a_failed_conversion_is_a_pdf_error(mocker: MockerFixture) -> None:
    def fail(source: Path, target: Path) -> None:
        raise subprocess.CalledProcessError(1, "soffice")

    mocker.patch.object(pdf, "_converter", return_value=fail)

    with pytest.raises(PdfError, match="cannot be made"):
        to_pdf(b"docx")


def test_libreoffice_is_preferred_and_configurable(
    settings: Settings,
    mocker: MockerFixture,
) -> None:
    settings.SOFFICE_PATH = "/opt/office/soffice"
    run = mocker.patch.object(pdf.subprocess, "run")

    with pytest.raises(PdfError):  # the mocked run writes no file
        to_pdf(b"docx")

    command = run.call_args.args[0]
    assert command[0] == "/opt/office/soffice"
    assert "--convert-to" in command


def test_a_pdf_needs_view_permission(client: Client, chapter: Chapter) -> None:
    assert client.get(reverse("reports:capacity-pdf")).status_code in (302, 403)


# --- capacity pivot -----------------------------------------------------------------------


def test_the_capacity_pivot_page_has_a_table_per_faculty(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    response = admin_client.get(reverse("reports:capacity-pivot"))

    tree = HTMLParser(response.content)
    names = [heading.text(strip=True) for heading in tree.css("section h3")]

    assert names == [
        f.faculty.name for f in Chapter.objects.get_snapshot(chapter.pk).report().faculties
    ]
    assert len(tree.css("section table")) == len(names)
    assert reverse("reports:capacity-pivot-pdf") in response.content.decode()


def test_the_capacity_report_links_to_its_pivot_and_pdf(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    content = admin_client.get(reverse("reports:capacity")).content.decode()

    assert reverse("reports:capacity-pivot") in content
    assert reverse("reports:capacity-pdf") in content


def test_the_capacity_pivot_holds_the_reports_head_counts(chapter: Chapter) -> None:
    report = Chapter.objects.get_snapshot(chapter.pk).report()

    context = documents.chapter_context(chapter, ReportChoices.CAPACITY_PIVOT)

    for row, faculty in zip(context["faculties"], report.faculties, strict=True):
        counted, signed = faculty.counted, faculty.signed

        assert split(row["specialized"]["fulltime_staff"]) == (
            counted.specialized_fulltime_staff,
            signed.specialized_fulltime_staff,
        )
        assert split(row["supported"]["parttime"]) == (
            counted.supported_parttime,
            signed.supported_parttime,
        )
        assert split(row["masters"]) == (counted.masters, signed.masters)

        totals = [split(row[kind]["total"]) for kind in ("specialized", "supported")]
        assert sum(c for c, _s in totals) == counted.phds
        assert sum(s for _c, s in totals) == signed.phds


def test_the_capacity_pivot_downloads_a_docx(admin_client: Client, chapter: Chapter) -> None:
    response = admin_client.get(reverse("reports:capacity-pivot-docx"))

    assert response["Content-Type"] == DOCX_CONTENT_TYPE

    content = b"".join(response.streaming_content)
    text = docx_text(content)
    faculties = list(Faculty.objects.for_chapter(chapter.pk).values_list("name", flat=True))

    assert all(name in text for name in faculties)
    assert len(Document(BytesIO(content)).tables) == 1 + len(faculties)  # the summary, then each
    assert "{{" not in text


# --- faculty staff pivot ------------------------------------------------------------------


def test_the_faculty_pivot_counts_its_staff_by_specialization(
    chapter: Chapter,
    faculty: Faculty,
) -> None:
    [faculty] = Faculty.objects.attach_reports([faculty], chapter.pk)
    report = faculty.report

    context = documents.faculty_report_context(chapter, faculty, ReportChoices.FACULTY_STAFF_PIVOT)

    rows = context["specializations"]
    assert [row["name"] for row in rows] == [s.name for s in report.faculty.faculty.specializations]
    assert {row["type"] for row in rows} <= {"specialized", "supported"}

    counted, signed = split(context["totals"]["total"])
    assert counted == len(report.counted_contracts)
    assert signed == len(report.included)
    assert sum(split(row["total"])[1] for row in rows) == signed
    assert split(context["totals"]["masters"]) == (report.counted.masters, report.signed.masters)


def test_the_faculty_pivot_page_and_docx(admin_client: Client, faculty: Faculty) -> None:
    page = admin_client.get(reverse("reports:staff-pivot", args=(faculty.pk,)))
    file = admin_client.get(reverse("reports:staff-pivot-docx", args=(faculty.pk,)))

    tree = HTMLParser(page.content)
    names = [row.css("td")[1].text(strip=True) for row in tree.css("tbody tr")]
    text = docx_text(b"".join(file.streaming_content))

    assert page.status_code == 200
    assert names
    assert all(name in text for name in names)
    assert faculty.name in text
    assert "{{" not in text


def test_the_staff_report_names_each_teachers_type(admin_client: Client, faculty: Faculty) -> None:
    response = admin_client.get(reverse("reports:staff-docx", args=(faculty.pk,)))

    document = Document(BytesIO(b"".join(response.streaming_content)))
    staff = next(table for table in document.tables if len(table.columns) == 7)
    types = {row.cells[3].text for row in staff.rows[1:]}

    assert staff.rows[0].cells[3].text == "specialization type"
    assert types <= {"specialized", "supported", ""}
    assert types & {"specialized", "supported"}
