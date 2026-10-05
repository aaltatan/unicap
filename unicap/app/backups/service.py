"""Taking, uploading and restoring backups (imported as `from ..backups import service`).

Every restore first saves a backup of what it replaces, so a restore can be undone by
restoring that one.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.translation import gettext as _

from ..choices import BackupScopeChoices
from ..exceptions import UserError
from ..models import Backup, Chapter, User
from .payload import (
    FORMAT,
    SECTIONS,
    VERSION,
    dump_chapter,
    dump_settings,
    load_chapter,
    load_settings,
)

MAX_UPLOAD = 50 * 1024 * 1024  # 50 MB


def create(
    scope: str,
    *,
    chapter: Chapter | None = None,
    section: str = "",
    user: User | None = None,
    notes: str = "",
) -> Backup:
    """Save a backup of everything, of `chapter`, or of `chapter`'s `section`.

    Raises:
        UserError: a chapter or section backup without its chapter, or an unknown section.

    Example:
        ```python
        service.create("section", chapter=chapter, section="faculties", user=request.user)
        ```
    """
    data = _dump(scope, chapter, section)

    return _save(data, scope=scope, chapter=chapter, section=section, user=user, notes=notes)


def upload(file: UploadedFile, *, user: User | None = None, notes: str = "") -> Backup:
    """Save a backup file downloaded earlier (from this app or another installation).

    Raises:
        UserError: the file is too big, not JSON, or not a backup of this app.
    """
    if file.size and file.size > MAX_UPLOAD:
        raise UserError(_("the file is too big (50 MB at most)."))

    data = _parse(file.read())

    chapters = data["chapters"]
    name = chapters[0].get("name", "") if len(chapters) == 1 else ""
    chapter = Chapter.objects.filter(name=name).first() if name else None

    return _save(
        data,
        scope=data["scope"],
        chapter=chapter,
        chapter_name=name,
        section=data.get("section", ""),
        user=user,
        notes=notes or _("uploaded: %(name)s") % {"name": file.name},
    )


def restore(
    backup: Backup,
    *,
    chapter: Chapter | None = None,
    new_chapter: str = "",
    user: User | None = None,
) -> Backup:
    """Bring the data back to `backup`; return the backup saved of what it replaced.

    - a system backup replaces every chapter and the settings;
    - a chapter backup replaces `chapter` (default: the one it was taken from), or becomes
      a new chapter named `new_chapter`;
    - a section backup replaces that section of `chapter` (default: its own chapter).

    Raises:
        UserError: no chapter to restore into, or rows refer to names that are not there.
        DomainError: the restored chapter would break a domain rule; nothing changes.
    """
    data = _parse(_read(backup))

    if backup.scope == BackupScopeChoices.SYSTEM:
        return _restore_system(data, user)

    payload = data["chapters"][0]

    if new_chapter:
        return _restore_as_new(payload, new_chapter, user)

    target = chapter or backup.chapter

    if target is None:
        raise UserError(_("choose the chapter to restore into: the backup's chapter is gone."))

    safety = create(
        backup.scope,
        chapter=target,
        section=backup.section,
        user=user,
        notes=_("before restoring: %(backup)s") % {"backup": backup},
    )

    with Chapter.objects.validated(target.pk):
        load_chapter(target, payload, settings=backup.scope == BackupScopeChoices.CHAPTER)

    return safety


def _restore_system(data: dict[str, Any], user: User | None) -> Backup:
    safety = create(
        BackupScopeChoices.SYSTEM,
        user=user,
        notes=_("before restoring the whole system"),
    )

    with transaction.atomic():
        Chapter.objects.all().delete()

        for payload in data["chapters"]:
            chapter = Chapter.objects.create(
                name=payload["name"],
                is_default=payload.get("is_default", False),
            )
            with Chapter.objects.validated(chapter.pk):
                load_chapter(chapter, payload, settings=True)

        load_settings(data.get("settings", {}))

    return safety


def _restore_as_new(payload: dict[str, Any], name: str, user: User | None) -> Backup:
    if Chapter.objects.filter(name=name).exists():
        raise UserError(_("a chapter named %(name)s exists already.") % {"name": name})

    with transaction.atomic():
        chapter = Chapter.objects.create(name=name)

        with Chapter.objects.validated(chapter.pk):
            load_chapter(chapter, payload, settings=True)

    return create(
        BackupScopeChoices.CHAPTER,
        chapter=chapter,
        user=user,
        notes=_("restored as a new chapter"),
    )


def _dump(scope: str, chapter: Chapter | None, section: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "format": FORMAT,
        "version": VERSION,
        "scope": scope,
        "created_at": timezone.now().isoformat(),
    }

    if scope == BackupScopeChoices.SYSTEM:
        chapters = Chapter.objects.order_by("name")
        return {
            **data,
            "settings": dump_settings(),
            "chapters": [dump_chapter(c) for c in chapters],
        }

    if chapter is None:
        raise UserError(_("choose a chapter to back up."))

    if scope == BackupScopeChoices.CHAPTER:
        return {**data, "chapters": [dump_chapter(chapter)]}

    if section not in SECTIONS:
        msg = _("unknown section %(section)s: %(sections)s") % {
            "section": section,
            "sections": ", ".join(SECTIONS),
        }
        raise UserError(msg)

    return {**data, "section": section, "chapters": [dump_chapter(chapter, [section])]}


def _save(  # noqa: PLR0913 - what the backup holds, and who took it why
    data: dict[str, Any],
    *,
    scope: str,
    chapter: Chapter | None,
    section: str,
    user: User | None,
    notes: str,
    chapter_name: str = "",
) -> Backup:
    content = json.dumps(data, ensure_ascii=False, indent=1, default=_json).encode("utf-8")

    stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    parts = [scope, section, chapter.name if chapter else chapter_name, stamp]
    filename = get_valid_filename("-".join(part for part in parts if part)) + ".json"

    backup = Backup(
        scope=scope,
        section=section,
        chapter=chapter,
        chapter_name=chapter.name if chapter else chapter_name,
        size=len(content),
        created_by=user if user and user.is_authenticated else None,
        notes=notes,
    )
    backup.file.save(filename, ContentFile(content), save=False)
    backup.save()

    return backup


def _read(backup: Backup) -> bytes:
    with backup.file.open("rb") as file:
        return file.read()


def _parse(content: bytes) -> dict[str, Any]:
    """The backup's data, checked: this app's format, a known scope, chapters as lists."""
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UserError(_("this file is not a backup: %(error)s") % {"error": error}) from error

    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise UserError(_("this file is not a backup of this app."))

    if data.get("version") != VERSION:
        raise UserError(
            _("this backup's version is not supported: %(v)s") % {"v": data.get("version")}
        )

    if data.get("scope") not in BackupScopeChoices.values or not isinstance(
        data.get("chapters"), list
    ):
        raise UserError(_("this backup is incomplete."))

    if data["scope"] != BackupScopeChoices.SYSTEM and len(data["chapters"]) != 1:
        raise UserError(_("this backup is incomplete."))

    return data


def _json(value: object) -> object:
    """Dates and decimals, as JSON can hold them."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    msg = f"{type(value).__name__} cannot be saved in a backup"
    raise TypeError(msg)
