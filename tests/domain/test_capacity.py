from fractions import Fraction

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    MEDICINE,
    PHARMACY,
    faculty,
    fulltime_borrowed,
    fulltime_staff,
    master,
    parttime,
    specialized,
)
from unicap.domain import (
    Chapter,
    ChapterFaculty,
    ContractStatus,
    DomainError,
    ViolationKind,
    evaluate_chapter,
    evaluate_faculty,
)
from unicap.domain.utils import share_cap


class TestCounting:
    def test_parttime_beyond_fulltime_of_same_type_is_not_counted(
        self, dentistry: ChapterFaculty
    ) -> None:
        first, second, last = parttime(DENTISTRY), parttime(DENTISTRY), parttime(DENTISTRY)

        contracts = [fulltime_staff(DENTISTRY), fulltime_borrowed(DENTISTRY), first, second, last]

        report = evaluate_faculty(dentistry, contracts)

        assert report.statuses[first] is ContractStatus.COUNTED
        assert report.statuses[second] is ContractStatus.COUNTED
        assert report.statuses[last] is ContractStatus.PARTTIME_OVERFLOW
        assert report.overflowing_phds == (last,)

    def test_supported_fulltime_does_not_cover_specialized_parttime(
        self, dentistry: ChapterFaculty
    ) -> None:
        specialized_parttime = parttime(DENTISTRY)

        report = evaluate_faculty(dentistry, [fulltime_staff(BIOLOGY), specialized_parttime])

        assert report.statuses[specialized_parttime] is ContractStatus.PARTTIME_OVERFLOW

    def test_masters_are_capped_by_specialized_fulltime_and_worth_half(
        self, dentistry: ChapterFaculty
    ) -> None:
        extra_master = master(DENTISTRY)

        contracts = [
            fulltime_staff(DENTISTRY),
            fulltime_staff(DENTISTRY),
            fulltime_staff(BIOLOGY),
            master(DENTISTRY),
            master(DENTISTRY),
            extra_master,
        ]

        report = evaluate_faculty(dentistry, contracts)

        assert report.statuses[extra_master] is ContractStatus.MASTERS_OVERFLOW
        assert report.counted.masters == 2
        assert report.counted.phd_equivalents == 4
        assert report.capacity == 40

    def test_specialization_the_faculty_does_not_accept_is_not_counted(
        self, dentistry: ChapterFaculty
    ) -> None:
        pharmacist = fulltime_staff(PHARMACY)

        report = evaluate_faculty(dentistry, [pharmacist])

        assert report.statuses[pharmacist] is ContractStatus.SPECIALIZATION_NOT_ALLOWED
        assert report.uncounted == (pharmacist,)
        assert report.overflowing == ()
        assert report.capacity == 0

    def test_head_counts(self, dentistry: ChapterFaculty) -> None:
        contracts = [
            fulltime_staff(DENTISTRY),
            fulltime_borrowed(DENTISTRY),
            fulltime_staff(BIOLOGY),
            fulltime_borrowed(BIOLOGY),
            parttime(BIOLOGY),
            parttime(BIOLOGY),
            parttime(BIOLOGY),
            master(BIOLOGY),
        ]

        report = evaluate_faculty(dentistry, contracts)

        assert report.signed.specialized_fulltime_staff == 1
        assert report.signed.specialized_fulltime_borrowed == 1
        assert report.signed.supported_fulltime_staff == 1
        assert report.signed.supported_fulltime_borrowed == 1
        assert report.signed.supported_parttime == 3
        assert report.counted.supported_parttime == 2
        assert report.counted.masters == 1

    def test_statuses_keep_the_signing_order(self, dentistry: ChapterFaculty) -> None:
        contracts = [parttime(DENTISTRY), fulltime_staff(PHARMACY), fulltime_staff(DENTISTRY)]

        report = evaluate_faculty(dentistry, contracts)

        assert list(report.statuses) == contracts


class TestStaffRatio:
    def test_overflowing_parttime_still_lowers_staff_ratio(self, dentistry: ChapterFaculty) -> None:
        contracts = [fulltime_staff(DENTISTRY), parttime(DENTISTRY), parttime(DENTISTRY)]

        report = evaluate_faculty(dentistry, contracts)

        assert report.staff_percentage == Fraction(100, 3)
        assert [v.kind for v in report.violations] == [ViolationKind.STAFF_RATIO_TOO_LOW]

    def test_half_staff_is_compliant(self, dentistry: ChapterFaculty) -> None:
        contracts = [fulltime_staff(DENTISTRY), fulltime_borrowed(DENTISTRY)]

        assert evaluate_faculty(dentistry, contracts).is_compliant

    def test_empty_faculty_is_compliant(self, dentistry: ChapterFaculty) -> None:
        report = evaluate_faculty(dentistry, [])

        assert report.is_compliant
        assert report.capacity == 0


class TestShares:
    def test_specialization_above_its_max_share_drops_parttime_first(
        self, dentistry_with_shares: ChapterFaculty
    ) -> None:
        dentist_parttime = parttime(DENTISTRY)

        contracts = [
            dentist_parttime,
            fulltime_staff(DENTISTRY),
            fulltime_staff(DENTISTRY),
            fulltime_staff(DENTISTRY),
            fulltime_staff(BIOLOGY),
            fulltime_staff(MEDICINE),
        ]

        report = evaluate_faculty(dentistry_with_shares, contracts)

        # 4 dentists of 6 PhDs = 66% > 60% -> keep 3 of 5 = 60%
        assert report.uncounted == (dentist_parttime,)
        assert report.statuses[dentist_parttime] is ContractStatus.SHARE_OVERFLOW
        assert report.capacity == 50
        assert report.is_compliant

    def test_missing_specialization_is_a_violation(
        self, dentistry_with_shares: ChapterFaculty
    ) -> None:
        report = evaluate_faculty(
            dentistry_with_shares, [fulltime_staff(DENTISTRY), fulltime_staff(BIOLOGY)]
        )

        # biology alone would be 50% > 25%, and dropping it leaves dentistry at 100% > 60%
        assert report.capacity == 0
        assert ViolationKind.SPECIALIZATION_SHARE_TOO_LOW in [v.kind for v in report.violations]

    @pytest.mark.parametrize(
        ("total", "percentage", "expected"),
        [(10, 60, 6), (5, 60, 3), (6, 60, 3), (100, 0.29, 0), (100, 29, 29), (3, 100, 3)],
    )
    def test_share_cap_is_floored_and_exact(
        self, total: int, percentage: float, expected: int
    ) -> None:
        assert share_cap(total, percentage) == expected


class TestChapterReport:
    def test_board_status_of_each_card(self, dentistry: ChapterFaculty) -> None:
        counted = fulltime_staff(DENTISTRY, dentistry)
        overflowing = parttime(BIOLOGY, dentistry)
        unsigned = parttime(DENTISTRY)

        chapter = Chapter.assemble("2026", (counted, overflowing, unsigned), faculties=(dentistry,))

        report = evaluate_chapter(chapter)

        assert report.status_of(counted.employee) is ContractStatus.COUNTED
        assert report.status_of(overflowing.employee) is ContractStatus.PARTTIME_OVERFLOW
        assert report.status_of(unsigned.employee) is None
        assert report.overflowing == (overflowing,)

    def test_previewing_a_drop_recolors_the_board(self, dentistry: ChapterFaculty) -> None:
        waiting = parttime(DENTISTRY)
        chapter = Chapter.assemble(
            "2026", (fulltime_staff(DENTISTRY, dentistry), waiting), faculties=(dentistry,)
        )

        preview = evaluate_chapter(chapter.move(waiting.employee, dentistry.faculty))

        assert preview.status_of(waiting.employee) is ContractStatus.COUNTED
        assert preview.capacity == 20
        assert preview.is_compliant

    def test_every_faculty_gets_a_report(
        self, dentistry: ChapterFaculty, pharmacy: ChapterFaculty
    ) -> None:
        report = evaluate_chapter(Chapter.assemble("2026", faculties=(dentistry, pharmacy)))

        assert report.report_of(pharmacy.faculty).capacity == 0
        assert len(report.faculties) == 2


class TestStudentNumbers:
    @staticmethod
    def faculty(name: str = "Dentistry", **numbers: int) -> ChapterFaculty:
        return faculty(name, specialized(DENTISTRY), **numbers)  # type: ignore[arg-type]

    def test_max_students_caps_the_capacity(self) -> None:
        dental = self.faculty(max_students=25)

        report = evaluate_faculty(dental, [fulltime_staff(DENTISTRY) for _ in range(4)])

        assert (report.teaching_capacity, report.capacity) == (40, 25)

        assert report.unused_teaching_capacity == 15

    def test_target_shortfall(self) -> None:
        report = evaluate_faculty(self.faculty(target_students=50), [fulltime_staff(DENTISTRY)])

        assert report.target_shortfall == 40

    def test_current_students_above_capacity_is_a_violation(self) -> None:
        report = evaluate_faculty(self.faculty(current_students=25), [fulltime_staff(DENTISTRY)])

        assert [v.kind for v in report.violations] == [ViolationKind.CURRENT_STUDENTS_OVER_CAPACITY]

        assert (report.seat_shortage, report.free_seats) == (15, -15)

    def test_free_seats(self) -> None:
        contracts = [fulltime_staff(DENTISTRY), fulltime_staff(DENTISTRY)]

        report = evaluate_faculty(self.faculty(current_students=12), contracts)

        assert report.is_compliant

        assert report.free_seats == 8

    def test_chapter_capacity_is_capped_by_its_max(self) -> None:
        dental = self.faculty()

        contracts = tuple(fulltime_staff(DENTISTRY, dental) for _ in range(3))

        report = evaluate_chapter(Chapter.assemble("2026", contracts, 25, faculties=(dental,)))

        assert (report.faculties_capacity, report.capacity) == (30, 25)

    def test_chapter_max_limit_is_the_sum_of_faculty_maximums(self) -> None:
        small, big = self.faculty(max_students=100), self.faculty("Big")

        assert Chapter.assemble("2026", faculties=(small, big)).max_limit is None

        big = self.faculty("Big", max_students=50)

        assert Chapter.assemble("2026", max_students=150, faculties=(small, big)).max_limit == 150

        with pytest.raises(DomainError, match="limit"):
            Chapter.assemble("2026", max_students=151, faculties=(small, big))
