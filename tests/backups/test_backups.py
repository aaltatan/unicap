"""Backups: the whole system, a chapter or a section, each restored on its own."""

import json
from pathlib import Path

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from pytest_django.fixtures import Settings
from selectolax.parser import HTMLParser

from tests.conftest import htmx
from unicap.app.backups import service
from unicap.app.exceptions import UserError
from unicap.app.models import AppSettings, Backup, Chapter, Faculty, User


@pytest.fixture(autouse=True)
def media(settings: Settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path


def counts(chapter: Chapter) -> tuple[int, int, int, int]:
    return (
        chapter.specializations.count(),
        chapter.faculties.count(),
        chapter.employees.count(),
        chapter.contracts.count(),
    )


def signing(chapter: Chapter) -> list[tuple[str, str | None]]:
    """Who is signed where, in signing order."""
    return list(
        chapter.contracts.order_by("position", "pk").values_list("employee__name", "faculty__name"),
    )


# --- chapters -----------------------------------------------------------------------------


def test_a_chapter_backup_brings_every_row_back(chapter: Chapter) -> None:
    before, placements = counts(chapter), signing(chapter)
    backup = service.create("chapter", chapter=chapter)

    chapter.contracts.all().delete()
    chapter.employees.all().delete()
    Faculty.objects.filter(chapter=chapter).update(notes="changed")

    service.restore(backup)

    assert counts(chapter) == before
    assert signing(chapter) == placements
    assert not chapter.faculties.filter(notes="changed").exists()


def test_a_chapter_backup_can_become_a_new_chapter(chapter: Chapter) -> None:
    backup = service.create("chapter", chapter=chapter)

    service.restore(backup, new_chapter="what if")

    copy = Chapter.objects.get(name="what if")
    assert counts(copy) == counts(chapter)
    assert [name for name, _ in signing(copy)] == [name for name, _ in signing(chapter)]


def test_a_restore_first_saves_what_it_replaces(chapter: Chapter) -> None:
    backup = service.create("chapter", chapter=chapter)

    safety = service.restore(backup)

    assert safety.pk != backup.pk
    assert safety.scope == "chapter"
    assert Backup.objects.count() == 2


# --- sections -----------------------------------------------------------------------------


def test_a_section_restores_on_its_own(chapter: Chapter) -> None:
    backup = service.create("section", chapter=chapter, section="faculties")
    faculty = chapter.faculties.first()
    name = faculty.name

    faculty.name = "Renamed"
    faculty.save()
    chapter.specializations.update(notes="kept")  # another section: not in the backup

    service.restore(backup)

    assert chapter.faculties.filter(name=name).exists()
    assert not chapter.faculties.filter(name="Renamed").exists()
    assert not chapter.specializations.exclude(notes="kept").exists()


def test_a_section_backup_holds_only_its_section(chapter: Chapter) -> None:
    backup = service.create("section", chapter=chapter, section="employees")

    data = json.loads(backup.file.read())

    assert set(data["chapters"][0]) - {
        "name",
        "max_students",
        "is_default",
        "notes",
    } == {"employees"}


def test_a_section_still_used_elsewhere_is_not_removed(chapter: Chapter) -> None:
    backup = service.create("section", chapter=chapter, section="specializations")
    before = counts(chapter)

    chapter.specializations.create(name="Astrology")  # not in the backup: removed on restore
    used = chapter.employees.first().specialization
    data = json.loads(backup.file.read())
    data["chapters"][0]["specializations"] = [
        row for row in data["chapters"][0]["specializations"] if row["name"] != used.name
    ]
    trimmed = service.upload(SimpleUploadedFile("trimmed.json", json.dumps(data).encode()))

    with pytest.raises(UserError, match=used.name):
        service.restore(trimmed, chapter=chapter)

    assert chapter.specializations.filter(name="Astrology").exists()  # rolled back
    assert counts(chapter)[0] == before[0] + 1


# --- the whole system ---------------------------------------------------------------------


def test_a_system_backup_brings_back_every_chapter_and_the_settings(chapter: Chapter) -> None:
    AppSettings.objects.update_or_create(pk=1, defaults={"project_name": "Before"})
    before, placements = counts(chapter), signing(chapter)
    backup = service.create("system")

    chapter.delete()
    AppSettings.objects.update_or_create(pk=1, defaults={"project_name": "After"})

    service.restore(backup)

    restored = Chapter.objects.get(name="2026 / Fall")
    assert counts(restored) == before
    assert signing(restored) == placements
    assert AppSettings.objects.get().project_name == "Before"


# --- files --------------------------------------------------------------------------------


def test_a_downloaded_backup_uploads_back(chapter: Chapter) -> None:
    backup = service.create("chapter", chapter=chapter)

    uploaded = service.upload(SimpleUploadedFile("chapter.json", backup.file.read()))

    assert uploaded.scope == "chapter"
    assert uploaded.chapter == chapter


@pytest.mark.django_db
@pytest.mark.parametrize(
    "content",
    [b"not json", b'{"format": "other"}', b'{"format": "unicap-backup", "version": 9}'],
)
def test_other_files_are_refused(content: bytes) -> None:
    with pytest.raises(UserError):
        service.upload(SimpleUploadedFile("backup.json", content))


# --- pages --------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["viewers", "editors", "managers"])
def test_backups_are_for_admins_by_default(client: Client, chapter: Chapter, role: str) -> None:
    user = User.objects.create_user("someone", password="password")  # noqa: S106
    user.groups.add(Group.objects.get(name=role))
    client.force_login(user)

    assert client.get(reverse("backups:index")).status_code == 403


def test_a_section_is_backed_up_from_its_table(admin_client: Client, chapter: Chapter) -> None:
    table = reverse("edu:faculties:index")

    html = HTMLParser(admin_client.get(table).content)
    assert html.css_first(f"form[action='{reverse('backups:create')}'] input[value='faculties']")

    response = admin_client.post(
        reverse("backups:create"),
        {"scope": "section", "section": "faculties", "chapter": chapter.pk, "next": table},
    )

    assert response.status_code == 302
    assert response.url == table
    assert Backup.objects.get().section == "faculties"


def test_a_backup_is_restored_from_its_page(admin_client: Client, chapter: Chapter) -> None:
    backup = service.create("chapter", chapter=chapter)
    before = counts(chapter)
    chapter.contracts.all().delete()

    form = admin_client.get(reverse("backups:restore", args=(backup.pk,)), **htmx())
    response = admin_client.post(
        reverse("backups:restore", args=(backup.pk,)),
        {"chapter": chapter.pk},
        **htmx(),
    )

    assert form.status_code == 200
    assert response["HX-Redirect"] == reverse("backups:index")
    assert counts(chapter) == before


def test_a_system_backup_is_restored_from_its_page(admin_client: Client, chapter: Chapter) -> None:
    """Its form has no field: the POST is empty (HTMX sends the CSRF token as a header)."""
    backup = service.create("system")
    before = counts(chapter)
    chapter.contracts.all().delete()

    response = admin_client.post(reverse("backups:restore", args=(backup.pk,)), **htmx())

    assert response["HX-Redirect"] == reverse("backups:index")
    assert counts(Chapter.objects.get(name=chapter.name)) == before
    assert Backup.objects.count() == 2  # the backup, and the one of what it replaced


def test_a_backup_downloads_as_json(admin_client: Client, chapter: Chapter) -> None:
    backup = service.create("system")

    response = admin_client.get(reverse("backups:download", args=(backup.pk,)))

    assert response["Content-Type"] == "application/json"
    assert json.loads(b"".join(response.streaming_content))["scope"] == "system"
