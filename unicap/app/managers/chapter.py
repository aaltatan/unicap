from collections.abc import Collection, Iterable, Iterator, Mapping
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from django.db import models, transaction
from django.db.models import Max
from django.utils.translation import gettext as _

from unicap import domain

from ..exceptions import UserError
from ..querysets import ChapterQuerySet
from ..snapshot import Snapshot
from .base import BaseManager

if TYPE_CHECKING:
    from ..models import Chapter


class ChapterManager(BaseManager.from_queryset(ChapterQuerySet)):  # type: ignore[misc]
    """The chapters' public API: reads, validation and whole-chapter writes."""

    # --- reads ----------------------------------------------------------------------

    def get_default(self) -> "Chapter | None":
        """The default chapter, else the first one (None when there is no chapter)."""
        return self.filter(is_default=True).first() or self.order_by("pk").first()

    def get_domain(self, chapter_id: int) -> domain.Chapter:
        """Build (and so validate) the domain chapter.

        Raises:
            DomainError: when the stored rows break a domain rule.
        """
        return self.with_domain_relations().get(pk=chapter_id).to_domain()

    def get_snapshot(self, chapter_id: int) -> Snapshot:
        """The domain chapter plus the ids to write placements back."""
        chapter = self.with_domain_relations().get(pk=chapter_id)

        specializations = {s.pk: s.to_domain() for s in chapter.specializations.all()}

        faculties = {
            f.pk: f.to_domain(specializations=specializations) for f in chapter.faculties.all()
        }

        employees = {
            e.pk: e.to_domain(specializations=specializations) for e in chapter.employees.all()
        }

        contracts = sorted(chapter.contracts.all(), key=lambda c: (c.position, c.pk))

        by_faculty = {pk: item.faculty for pk, item in faculties.items()}

        value = domain.Chapter(
            chapter.name,
            tuple(c.to_domain(employees=employees, faculties=by_faculty) for c in contracts),
            chapter.max_students,
            faculties=tuple(faculties.values()),
            specializations=tuple(specializations.values()),
            employees=tuple(employees.values()),
        )

        return Snapshot(
            chapter_id=chapter.pk,
            chapter=value,
            faculty_ids={item.faculty: pk for pk, item in faculties.items()},
            contract_ids={employees[c.employee_id]: c.pk for c in contracts},
            employees=employees,
        )

    # --- validation -----------------------------------------------------------------

    @contextmanager
    def validated(self, chapter_id: int) -> Iterator[None]:
        """One transaction that commits only if the whole chapter is still valid.

        Raises:
            DomainError: the chapter would break a domain rule; nothing is saved.

        Example:
            ```python
            with Chapter.objects.validated(chapter.pk):
                faculty.save()
            ```
        """
        with transaction.atomic():
            # one write to a chapter at a time: two that are each valid alone could
            # otherwise both commit and break a rule together (MySQL locks the row;
            # SQLite, with one writer at a time, ignores the lock)
            self.select_for_update().filter(pk=chapter_id).values_list("pk", flat=True).first()
            yield
            self.get_domain(chapter_id)

    # --- writes ---------------------------------------------------------------------

    def save_chapter(self, chapter: "Chapter") -> "Chapter":
        """Save a chapter's settings; the first chapter becomes the default.

        Raises:
            DomainError: max students above the faculties' limit; nothing is saved.
        """
        with transaction.atomic():
            if not self.exclude(pk=chapter.pk).exists():
                chapter.is_default = True

            chapter.save()

            self.get_domain(chapter.pk)

        return chapter

    def set_default(self, chapter: "Chapter") -> None:
        """Make this the chapter the app opens with."""
        with transaction.atomic():
            self.filter(is_default=True).exclude(pk=chapter.pk).update(is_default=False)
            self.filter(pk=chapter.pk).update(is_default=True)

    def bulk_set(self, ids: Iterable[int], values: Mapping[str, Any]) -> int:
        """Set the same settings on several chapters; each must stay valid, or none changes.

        Raises:
            DomainError: a chapter would break a domain rule; nothing is saved.
        """
        ids = list(ids)

        with transaction.atomic():
            changed = self.filter(pk__in=ids).update(**values)

            for chapter_id in ids:
                self.get_domain(chapter_id)

        return changed

    def delete_many(self, ids: Iterable[int]) -> int:
        """Delete chapters with everything they own; a default moves to a remaining one."""
        with transaction.atomic():
            deleted, _counts = self.filter(pk__in=list(ids)).delete()

            if not self.filter(is_default=True).exists() and (first := self.first()):
                self.set_default(first)

        return deleted

    def duplicate(self, chapter: "Chapter", name: str) -> "Chapter":
        """Copy a chapter with all of its rows (notes included), to try another scenario."""
        with transaction.atomic():
            copy = self.create(
                name=name,
                max_students=chapter.max_students,
                notes=chapter.notes,
            )

            specializations = {
                row.pk: _copy(row, chapter=copy) for row in chapter.specializations.all()
            }

            faculties = {}

            for faculty in chapter.faculties.prefetch_related("shares"):
                shares = list(faculty.shares.all())

                original_pk = faculty.pk  # _copy gives `faculty` a new pk

                faculties[original_pk] = _copy(faculty, chapter=copy)

                for share in shares:
                    _copy(
                        share,
                        faculty=faculties[original_pk],
                        specialization=specializations[share.specialization_id],
                    )

            employees = {}

            for employee in chapter.employees.prefetch_related("excluded_faculties"):
                excluded = [faculties[row.pk] for row in employee.excluded_faculties.all()]

                original_pk = employee.pk  # _copy gives `employee` a new pk

                employees[original_pk] = _copy(
                    employee,
                    chapter=copy,
                    specialization=specializations[employee.specialization_id],
                )
                employees[original_pk].excluded_faculties.set(excluded)

            for contract in chapter.contracts.all():
                _copy(
                    contract,
                    chapter=copy,
                    employee=employees[contract.employee_id],
                    faculty=faculties.get(contract.faculty_id or 0),
                )

            self.get_domain(copy.pk)

        return copy

    def create_from_domain(self, value: domain.Chapter, *, notes: str = "") -> "Chapter":
        """Save a whole domain chapter (settings and every row) as a new chapter.

        Each row goes through its model's `from_domain`; contracts keep their order.

        Raises:
            DomainError: the saved rows would not rebuild a valid chapter.
        """
        related = self._related_models()

        with transaction.atomic():
            chapter = self.model.from_domain(value)
            chapter.notes = notes
            chapter.is_default = not self.exists()
            chapter.save()

            specializations = {
                s: related["specializations"].from_domain(s, chapter_id=chapter.pk)
                for s in value.specializations
            }

            for row in specializations.values():
                row.save()

            faculties = {}

            for item in value.faculties:
                faculty = related["faculties"].from_domain(item, chapter_id=chapter.pk)
                faculty.save()
                faculties[item.faculty] = faculty

                for position, share in enumerate(item.shares):
                    related["shares"].from_domain(
                        share,
                        faculty_id=faculty.pk,
                        specialization_id=specializations[share.specialization].pk,
                        specialization_type=item.type_of(share.specialization),
                        position=position,
                    ).save()

            employees = {}

            for employee in value.employees:
                row = related["employees"].from_domain(
                    employee,
                    chapter_id=chapter.pk,
                    specialization_id=specializations[employee.specialization].pk,
                )
                row.save()
                row.excluded_faculties.set(
                    row_
                    for faculty, row_ in faculties.items()
                    if not employee.can_be_counted_in(faculty)
                )
                employees[employee] = row

            for position, contract in enumerate(value.contracts):
                faculty = faculties.get(contract.faculty) if contract.faculty else None

                related["contracts"].from_domain(
                    contract,
                    chapter_id=chapter.pk,
                    employee_id=employees[contract.employee].pk,
                    faculty_id=faculty.pk if faculty else None,
                    position=position,
                ).save()

            self.get_domain(chapter.pk)

        return chapter

    def _related_models(self) -> dict[str, Any]:
        """The chapter-owned models, through the relations (this app imports none of them)."""
        meta = self.model._meta  # noqa: SLF001

        related = {
            name: meta.get_field(name).related_model
            for name in ("specializations", "faculties", "employees", "contracts")
        }

        related["shares"] = related["faculties"]._meta.get_field("shares").related_model  # noqa: SLF001

        return related

    def reset(self, chapter: "Chapter") -> int:
        """Make every contract of the chapter unsigned (the board's Reset).

        Contracts locked to their faculty stay signed.
        """
        with self.validated(chapter.pk):
            return chapter.contracts.signed().movable().update(faculty=None)

    def apply_placements(
        self,
        chapter: "Chapter",
        placements: Mapping[int, int | None],
        *,
        substitutes: Mapping[int, int] | None = None,
        removed: Collection[int] = (),
    ) -> int:
        """Sign each contract id to its faculty id (None: unsigned); re-signed go last.

        Args:
            chapter: whose contracts are placed.
            placements: contract id -> faculty id (None: unsigned).
            substitutes: contract id -> the id of the contract that makes its move in its
                place (the domain's `substitutes_for`: the same in everything but who).
            removed: the contract ids left where they are, whatever `placements` says.

        Returns how many contracts moved.

        Raises:
            UserError: a faculty id is not one of the chapter's, a substitute is not one of
                its contract's, or a contract is locked to another faculty; nothing is saved.
            DomainError: the placement breaks a domain rule; nothing is saved.
        """
        moved = 0

        if substitutes or removed:
            placements = self.get_snapshot(chapter.pk).resolved(
                placements, removed=removed, substitutes=substitutes
            )

        asked = {faculty_id for faculty_id in placements.values() if faculty_id is not None}
        owned = set(chapter.faculties.filter(pk__in=asked).values_list("pk", flat=True))

        if asked - owned:
            raise UserError(_("a faculty of this placement is not in the chapter."))

        with self.validated(chapter.pk):
            position = self.next_position(chapter)

            placed = chapter.contracts.filter(pk__in=list(placements))

            chapter.contracts.check_placements(placements)

            for contract in placed.order_by("position"):
                faculty_id = placements[contract.pk]

                if contract.faculty_id == faculty_id:
                    continue

                contract.faculty_id = faculty_id
                contract.position = position
                contract.save(update_fields=("faculty", "position"))

                position += 1
                moved += 1

        return moved

    def next_position(self, chapter: "Chapter") -> int:
        """The signing position of a contract signed now: after every other."""
        last = chapter.contracts.aggregate(last=Max("position"))["last"]

        return 0 if last is None else last + 1


def _copy(row: models.Model, **changes: object) -> models.Model:
    """Save a copy of `row` with `changes` (a new primary key)."""
    row.pk = None
    row._state.adding = True  # noqa: SLF001

    for field, value in changes.items():
        setattr(row, field, value)

    row.save()

    return row
