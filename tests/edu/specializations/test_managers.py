import pytest

from tests.factories import SpecializationFactory
from unicap.app.exceptions import UserError
from unicap.app.models import Chapter, Specialization


def test_annotate_usage(chapter: Chapter) -> None:
    biology = Specialization.objects.annotate_usage().get(chapter=chapter, name="Biology")

    assert (biology.faculties_count, biology.employees_count) == (2, 5)


def test_a_used_specialization_cannot_be_deleted(chapter: Chapter) -> None:
    biology = Specialization.objects.get(chapter=chapter, name="Biology")

    with pytest.raises(UserError, match="still in use"):
        Specialization.objects.delete_many(chapter.pk, [biology.pk])

    assert Specialization.objects.filter(pk=biology.pk).exists()


def test_an_unused_one_can(chapter: Chapter) -> None:
    unused = SpecializationFactory(chapter=chapter, name="History")

    assert Specialization.objects.delete_many(chapter.pk, [unused.pk]) == 1


def test_delete_many_stays_in_its_chapter(chapter: Chapter) -> None:
    elsewhere = SpecializationFactory(name="History")

    assert Specialization.objects.delete_many(chapter.pk, [elsewhere.pk]) == 0
    assert Specialization.objects.filter(pk=elsewhere.pk).exists()


def test_switching_a_specialization_off_leaves_its_contracts_out(chapter: Chapter) -> None:
    biology = Specialization.objects.get(chapter=chapter, name="Biology")

    Specialization.objects.toggle_active(biology)

    counts = Chapter.objects.get_snapshot(chapter.pk).status_counts()

    assert counts["excluded"] == 5
