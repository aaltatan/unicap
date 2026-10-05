"""The capacity reports' numbers tell who they count: a tooltip of names, one per line."""

from django.test import Client
from django.urls import reverse
from selectolax.parser import HTMLParser

from unicap.app.choices import ReportChoices
from unicap.app.models import Chapter
from unicap.app.reports import documents
from unicap.app.reports.context import HEAD_COUNTS
from unicap.app.templatetags.domain import teacher_names


def unnumbered(lines: list[str]) -> list[str]:
    """The names of `1. Dr. Hind` lines."""
    return [line.split(". ", 1)[1] for line in lines]


def test_a_line_is_only_a_number_and_the_name(chapter: Chapter) -> None:
    faculty = Chapter.objects.get_snapshot(chapter.pk).report().faculties[1]
    names = [contract.employee.name for contract, status in faculty.in_staff_order]

    lines = teacher_names(faculty)["signed"]["all"].splitlines()

    assert lines
    assert all(line.split(". ", 1)[1] in names for line in lines)


def test_each_head_count_names_as_many_teachers_as_it_counts(chapter: Chapter) -> None:
    report = Chapter.objects.get_snapshot(chapter.pk).report()

    for faculty in report.faculties:
        names = teacher_names(faculty)

        for key, _label in HEAD_COUNTS:
            counted = names["counted"].get(key, "").splitlines()
            signed = names["signed"].get(key, "").splitlines()

            assert len(counted) == getattr(faculty.counted, key)
            assert len(signed) == getattr(faculty.signed, key)
            assert set(unnumbered(counted)) <= set(unnumbered(signed))

            for lines in (counted, signed):  # numbered from 1
                assert [line.split(". ", 1)[0] for line in lines] == [
                    str(index) for index in range(1, len(lines) + 1)
                ]

        everyone = {contract.employee.name for contract in faculty.counted_contracts}
        assert set(unnumbered(names["counted"].get("all", "").splitlines())) == everyone


def test_the_capacity_report_puts_the_names_on_its_numbers(
    admin_client: Client,
    chapter: Chapter,
) -> None:
    report = Chapter.objects.get_snapshot(chapter.pk).report()
    faculty = next(f for f in report.faculties if f.counted.specialized_fulltime_staff)
    names = teacher_names(faculty)

    tree = HTMLParser(admin_client.get(reverse("reports:capacity")).content)
    row = next(
        row
        for row in tree.css("main tbody tr")
        if row.css_first("td").text(strip=True) == faculty.faculty.name
    )
    counted, signed = row.css("td")[1].css("span")

    assert counted.text(strip=True) == str(faculty.counted.specialized_fulltime_staff)
    assert counted.attributes["title"] == names["counted"]["specialized_fulltime_staff"]
    assert signed.attributes["title"] == names["signed"]["specialized_fulltime_staff"]
    assert "\n" in signed.attributes["title"] or faculty.signed.specialized_fulltime_staff == 1


def test_the_pivot_names_the_counted_then_everyone_when_they_differ(chapter: Chapter) -> None:
    report = Chapter.objects.get_snapshot(chapter.pk).report()

    context = documents.chapter_context(chapter, ReportChoices.CAPACITY_PIVOT)

    for row, faculty in zip(context["faculties"], report.faculties, strict=True):
        names = teacher_names(faculty)
        cell = row["names"]["specialized"]["parttime"]
        counted = names["counted"].get("specialized_parttime", "")
        signed = names["signed"].get("specialized_parttime", "")

        if counted == signed:
            assert cell == signed
        else:
            assert cell == f"counted:\n{counted}\n\nsigned:\n{signed}"


def test_the_pivot_page_puts_the_names_on_its_cells(admin_client: Client, chapter: Chapter) -> None:
    tree = HTMLParser(admin_client.get(reverse("reports:capacity-pivot")).content)

    titled = [cell for cell in tree.css("main section tbody td[title]") if cell.attributes["title"]]

    assert titled
    assert all(
        cell.text(strip=True) == "0" or cell.attributes["title"]
        for cell in tree.css("main section tbody td[title]")
    )
