import pytest

from unicap.app.models import Chapter, Contract, Faculty
from unicap.domain import DomainError, Strategy


def test_first_chapter_is_the_default(chapter: Chapter) -> None:
    assert chapter.is_default
    assert Chapter.objects.get_default() == chapter


def test_snapshot_evaluates_the_sample(chapter: Chapter) -> None:
    snapshot = Chapter.objects.get_snapshot(chapter.pk)

    report = snapshot.report()

    assert report.capacity == 155  # the one master alone rounds down to no PhD
    assert not report.is_compliant
    assert len(report.overflowing) == 3
    assert snapshot.status_counts(report) == {
        "counted": 11,
        "uncounted": 3,
        "excluded": 0,
        "unsigned": 2,
    }


def test_lanes_hold_every_contract_once(chapter: Chapter) -> None:
    lanes = Chapter.objects.get_snapshot(chapter.pk).lanes()

    assert lanes[0].key == "unsigned"
    assert sum(len(lane.cards) for lane in lanes) == 16
    assert {card.contract_id for lane in lanes for card in lane.cards} == set(
        Contract.objects.for_chapter(chapter.pk).values_list("pk", flat=True),
    )


def test_drop_previews_cover_every_lane(chapter: Chapter) -> None:
    karim = Contract.objects.get(chapter=chapter, employee__name="Dr. Karim")

    snapshot = Chapter.objects.get_snapshot(chapter.pk)

    previews = {p.faculty_id: p for p in snapshot.drop_previews(karim.employee_id)}

    pharmacy = Faculty.objects.get(chapter=chapter, name="Pharmacy")
    dentistry = Faculty.objects.get(chapter=chapter, name="Dentistry")

    assert previews[None].status is None
    assert previews[pharmacy.pk].status.is_counted
    assert previews[pharmacy.pk].capacity == 170
    assert not previews[dentistry.pk].status.is_counted


def test_validated_rolls_back_a_broken_chapter(chapter: Chapter) -> None:
    faculty = Faculty.objects.get(chapter=chapter, name="Dentistry")

    with pytest.raises(DomainError), Chapter.objects.validated(chapter.pk):
        faculty.shares.filter(specialization__name="Dentistry").update(percentage=90)

    assert faculty.shares.get(specialization__name="Dentistry").percentage == 60


def test_save_chapter_refuses_a_max_above_the_faculties(chapter: Chapter) -> None:
    chapter.max_students = 10_000  # the faculties allow 80 + 120 + 200

    with pytest.raises(DomainError, match="cannot exceed"):
        Chapter.objects.save_chapter(chapter)

    chapter.refresh_from_db()
    assert chapter.max_students is None


def test_duplicate_copies_every_row(chapter: Chapter) -> None:
    chapter.notes = "keep me"
    chapter.save()

    copy = Chapter.objects.duplicate(chapter, "copy")

    original = Chapter.objects.get_snapshot(chapter.pk)
    duplicated = Chapter.objects.get_snapshot(copy.pk)

    assert copy.notes == "keep me"
    assert not copy.is_default
    assert duplicated.report().capacity == original.report().capacity
    assert copy.faculties.count() == chapter.faculties.count() == 3
    assert copy.contracts.count() == chapter.contracts.count() == 16
    assert not set(copy.contracts.values_list("pk", flat=True)) & set(
        chapter.contracts.values_list("pk", flat=True),
    )


def test_set_default_moves_it(chapter: Chapter) -> None:
    other = Chapter.objects.create(name="other")

    Chapter.objects.set_default(other)

    assert list(Chapter.objects.filter(is_default=True)) == [other]


def test_deleting_the_default_moves_it_to_a_remaining_one(chapter: Chapter) -> None:
    other = Chapter.objects.create(name="other")

    Chapter.objects.delete_many([chapter.pk])

    other.refresh_from_db()
    assert other.is_default


def test_reset_unsigns_every_contract(chapter: Chapter) -> None:
    assert Chapter.objects.reset(chapter) == 14

    assert not Contract.objects.for_chapter(chapter.pk).signed().exists()


def test_optimization_is_applied_as_previewed(chapter: Chapter) -> None:
    optimization = Chapter.objects.get_snapshot(chapter.pk).optimization(
        Strategy.MAXIMIZE_STUDENTS,
    )

    assert optimization.after.capacity > optimization.before.capacity

    moved = Chapter.objects.apply_placements(chapter, optimization.placements)

    assert moved == len(optimization.moves)
    assert Chapter.objects.get_snapshot(chapter.pk).report().capacity == (
        optimization.after.capacity
    )


def test_re_signed_contracts_go_last(chapter: Chapter) -> None:
    omar = Contract.objects.get(chapter=chapter, employee__name="Dr. Omar")

    Chapter.objects.apply_placements(chapter, {omar.pk: None})

    omar.refresh_from_db()
    others = Contract.objects.for_chapter(chapter.pk).exclude(pk=omar.pk)
    assert all(omar.position > position for position in others.values_list("position", flat=True))
