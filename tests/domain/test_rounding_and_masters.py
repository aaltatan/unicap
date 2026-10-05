"""Rounding modes, the chapter's masters policy, and masters as heads in share rows."""

from fractions import Fraction

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    MEDICINE,
    faculty,
    fulltime_borrowed,
    fulltime_staff,
    master,
    parttime,
    specialized,
    supported,
)
from unicap.domain import (
    ContractStatus,
    ContractType,
    DomainError,
    EmploymentType,
    RoundingMode,
    Share,
    TeacherKind,
    ViolationKind,
    evaluate_faculty,
    round_count,
)


class TestRoundCount:
    @pytest.mark.parametrize(
        ("value", "mode", "expected"),
        [
            (Fraction(3, 2), RoundingMode.FLOOR, 1),
            (Fraction(3, 2), RoundingMode.CEILING, 2),
            (Fraction(3, 2), RoundingMode.HALF_UP, 2),
            (Fraction(3, 2), RoundingMode.HALF_DOWN, 1),
            (Fraction(3, 2), RoundingMode.HALF_EVEN, 2),
            (Fraction(5, 2), RoundingMode.HALF_EVEN, 2),
            (Fraction(7, 5), RoundingMode.HALF_UP, 1),
            (Fraction(8, 5), RoundingMode.HALF_DOWN, 2),
            (Fraction(1, 10), RoundingMode.CEILING, 1),
            (Fraction(9, 10), RoundingMode.FLOOR, 0),
            (3, RoundingMode.CEILING, 3),
            (0, RoundingMode.CEILING, 0),
        ],
    )
    def test_each_mode(self, value: Fraction, mode: RoundingMode, expected: int) -> None:
        assert round_count(value, mode) == expected


class TestMastersPerRow:
    def test_masters_per_phd_must_be_positive(self) -> None:
        with pytest.raises(DomainError, match="masters per PhD"):
            Share(DENTISTRY, masters_per_phd=0)

    @pytest.mark.parametrize(
        ("per_phd", "rounding", "masters", "expected"),
        [
            (2, RoundingMode.FLOOR, 3, 1),
            (2, RoundingMode.CEILING, 3, 2),
            (2, RoundingMode.HALF_UP, 1, 1),
            (2, RoundingMode.HALF_DOWN, 1, 0),
            (3, RoundingMode.FLOOR, 5, 1),
            (3, RoundingMode.HALF_UP, 5, 2),
            (1, RoundingMode.FLOOR, 4, 4),
        ],
    )
    def test_the_row_and_the_faculty_set_the_masters_worth(
        self, per_phd: int, rounding: RoundingMode, masters: int, expected: int
    ) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY, masters_per_phd=per_phd),  # type: ignore[arg-type]
            masters_rounding=rounding,  # type: ignore[arg-type]
        )
        contracts = [fulltime_staff(DENTISTRY, dentistry) for _ in range(masters)]
        contracts += [master(DENTISTRY, dentistry) for _ in range(masters)]

        assert evaluate_faculty(dentistry, contracts).counted.masters_as_phds == expected

    def test_the_faculty_rounds_its_masters_summed(self) -> None:
        """One master of each of two specializations, two a PhD: one whole PhD, not 0 + 0."""
        dentistry = faculty(
            "Dentistry", specialized(DENTISTRY), specialized(BIOLOGY), students_per_phd=10
        )
        contracts = [fulltime_staff(DENTISTRY, dentistry), fulltime_staff(BIOLOGY, dentistry)]
        contracts += [master(DENTISTRY, dentistry), master(BIOLOGY, dentistry)]

        assert evaluate_faculty(dentistry, contracts).capacity == 30


class TestMastersLeftOutByRow:
    def test_a_row_without_masters_leaves_them_out(self) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY),
            supported(BIOLOGY, calculate_masters=False),  # type: ignore[arg-type]
        )

        specialist = master(DENTISTRY, dentistry)
        supporter = master(BIOLOGY, dentistry)

        contracts = [fulltime_staff(DENTISTRY, dentistry) for _ in range(2)]
        contracts += [specialist, supporter]

        report = evaluate_faculty(dentistry, contracts)

        assert report.statuses[specialist] is ContractStatus.COUNTED
        assert report.statuses[supporter] is ContractStatus.MASTERS_EXCLUDED
        assert report.counted.masters == 1
        assert report.signed.masters == 1  # left out: not even signed

    def test_on_by_default(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))

        supporter = master(BIOLOGY, dentistry)

        report = evaluate_faculty(dentistry, [fulltime_staff(DENTISTRY, dentistry), supporter])

        assert report.statuses[supporter] is ContractStatus.COUNTED


class TestContractTypePerRow:
    def test_only_the_rows_type_counts(self) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY),
            supported(BIOLOGY, contract_type=ContractType.FULLTIME),  # type: ignore[arg-type]
        )

        fulltime = fulltime_staff(BIOLOGY, dentistry)
        part = parttime(BIOLOGY, dentistry)

        report = evaluate_faculty(dentistry, [fulltime_staff(DENTISTRY, dentistry), fulltime, part])

        assert report.statuses[fulltime] is ContractStatus.COUNTED
        assert report.statuses[part] is ContractStatus.CONTRACT_TYPE_NOT_ALLOWED
        assert part in report.uncounted  # signed, so it still lowers the staff percentage

    def test_parttime_only(self) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY, contract_type=ContractType.PARTTIME),  # type: ignore[arg-type]
        )

        fulltime = fulltime_staff(DENTISTRY, dentistry)

        report = evaluate_faculty(dentistry, [fulltime])

        assert report.statuses[fulltime] is ContractStatus.CONTRACT_TYPE_NOT_ALLOWED
        assert report.capacity == 0


class TestMastersAreHeadsInShareRows:
    def test_max_teachers_counts_masters_and_drops_them_first(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY, max_teachers=3))

        phds = [fulltime_staff(DENTISTRY, dentistry) for _ in range(2)]
        masters = [master(DENTISTRY, dentistry) for _ in range(2)]

        report = evaluate_faculty(dentistry, [*masters, *phds])  # masters signed first

        assert [report.statuses[c] for c in phds] == [ContractStatus.COUNTED] * 2
        assert [report.statuses[c] for c in masters] == [
            ContractStatus.COUNTED,
            ContractStatus.TEACHERS_OVERFLOW,
        ]
        assert report.counted.phds + report.counted.masters == 3

    def test_max_share_is_of_every_counted_teacher(self) -> None:
        dentistry = faculty(
            "Dentistry",
            specialized(DENTISTRY),
            supported(BIOLOGY, max_percentage=10),
        )

        contracts = [fulltime_staff(DENTISTRY, dentistry) for _ in range(9)]
        biology = [fulltime_staff(BIOLOGY, dentistry), master(BIOLOGY, dentistry)]

        report = evaluate_faculty(dentistry, [*contracts, *biology])

        # 11 teachers: 10% is 1.1, rounded down to 1 biology teacher (the PhD)
        assert report.statuses[biology[0]] is ContractStatus.COUNTED
        assert report.statuses[biology[1]] is ContractStatus.SHARE_OVERFLOW

    def test_max_share_rounding_is_the_faculty_choice(self) -> None:
        def evaluate(rounding: RoundingMode) -> int:
            dentistry = faculty(
                "Dentistry",
                specialized(DENTISTRY),
                supported(BIOLOGY, max_percentage=25),
                max_share_rounding=rounding,  # type: ignore[arg-type]
            )
            contracts = [fulltime_staff(DENTISTRY, dentistry) for _ in range(4)]
            contracts += [fulltime_staff(BIOLOGY, dentistry) for _ in range(2)]

            return evaluate_faculty(dentistry, contracts).counted.supported_fulltime_staff

        # 25% of 6 = 1.5 biology teachers
        assert (evaluate(RoundingMode.FLOOR), evaluate(RoundingMode.CEILING)) == (1, 2)

    def test_min_teachers_counts_masters(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY, min_teachers=3))

        contracts = [fulltime_staff(DENTISTRY, dentistry) for _ in range(2)]
        contracts.append(master(DENTISTRY, dentistry))

        assert evaluate_faculty(dentistry, contracts).is_compliant

    def test_min_share_rounding_is_the_faculty_choice(self) -> None:
        def violations(rounding: RoundingMode) -> list[ViolationKind]:
            dentistry = faculty(
                "Dentistry",
                specialized(DENTISTRY),
                supported(MEDICINE, min_percentage=15),
                min_share_rounding=rounding,  # type: ignore[arg-type]
            )
            contracts = [fulltime_staff(DENTISTRY, dentistry) for _ in range(5)]

            return [v.kind for v in evaluate_faculty(dentistry, contracts).violations]

        # 15% of 5 = 0.75 medicine teachers: down needs none, up needs one
        assert violations(RoundingMode.FLOOR) == []
        assert violations(RoundingMode.CEILING) == [ViolationKind.SPECIALIZATION_SHARE_TOO_LOW]


class TestStaffRounding:
    def test_the_fewest_staff_round_the_faculty_way(self) -> None:
        def violations(rounding: RoundingMode) -> list[ViolationKind]:
            dentistry = faculty(
                "Dentistry",
                specialized(DENTISTRY),
                min_staff_percentage=50,
                staff_rounding=rounding,  # type: ignore[arg-type]
            )
            contracts = [fulltime_staff(DENTISTRY, dentistry)]
            contracts += [fulltime_borrowed(DENTISTRY, dentistry) for _ in range(2)]

            return [v.kind for v in evaluate_faculty(dentistry, contracts).violations]

        # 50% of 3 PhDs = 1.5 staff: down needs 1 (met), up needs 2 (missed)
        assert violations(RoundingMode.FLOOR) == []
        assert violations(RoundingMode.CEILING) == [ViolationKind.STAFF_RATIO_TOO_LOW]

    def test_parttime_still_lowers_the_staff_percentage(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY), min_staff_percentage=50)

        contracts = [fulltime_staff(DENTISTRY, dentistry), parttime(DENTISTRY, dentistry)]
        contracts.append(parttime(DENTISTRY, dentistry))  # overflows, still signed

        report = evaluate_faculty(dentistry, contracts)

        assert report.staff_percentage == Fraction(100, 3)
        assert [v.kind for v in report.violations] == [ViolationKind.STAFF_RATIO_TOO_LOW]


class TestComposition:
    def test_counted_teachers_by_employment_then_kind(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))

        contracts = [
            fulltime_staff(DENTISTRY, dentistry),
            fulltime_staff(BIOLOGY, dentistry),
            fulltime_borrowed(DENTISTRY, dentistry),
            parttime(DENTISTRY, dentistry),
            master(DENTISTRY, dentistry),
            parttime(BIOLOGY, dentistry),  # counted: up to the one supported fulltime
        ]

        slices = [
            (s.employment, s.kind, s.count)
            for s in evaluate_faculty(dentistry, contracts).composition
        ]

        assert slices == [
            (EmploymentType.STAFF, TeacherKind.SPECIALIZED_FULLTIME, 1),
            (EmploymentType.STAFF, TeacherKind.SUPPORTED_FULLTIME, 1),
            (EmploymentType.STAFF, TeacherKind.MASTER, 1),
            (EmploymentType.BORROWED, TeacherKind.SPECIALIZED_FULLTIME, 1),
            (EmploymentType.BORROWED, TeacherKind.SPECIALIZED_PARTTIME, 1),
            (EmploymentType.BORROWED, TeacherKind.SUPPORTED_PARTTIME, 1),
        ]

    def test_only_counted_teachers(self) -> None:
        dentistry = faculty("Dentistry", specialized(DENTISTRY))

        report = evaluate_faculty(dentistry, [parttime(DENTISTRY, dentistry)])  # overflows

        assert report.composition == ()
