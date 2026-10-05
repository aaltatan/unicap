from fractions import Fraction

import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    faculty,
    fulltime_borrowed,
    fulltime_staff,
    master,
    parttime,
    specialized,
    supported,
)
from unicap.domain import HeadCount, Mix, evaluate_faculty, mix_of


@pytest.mark.parametrize(
    ("heads", "expected"),
    [
        (HeadCount(), Mix()),
        (
            HeadCount(specialized_fulltime_staff=3, supported_parttime=1),
            Mix(
                specialized=Fraction(75),
                supported=Fraction(25),
                fulltime=Fraction(75),
                parttime=Fraction(25),
                phds=Fraction(100),
            ),
        ),
        (
            HeadCount(specialized_fulltime_borrowed=1, supported_fulltime_staff=1, masters=2),
            Mix(
                specialized=Fraction(50),
                supported=Fraction(50),
                fulltime=Fraction(100),
                phds=Fraction(50),
                masters=Fraction(50),
            ),
        ),
        (HeadCount(masters=3), Mix(masters=Fraction(100))),
    ],
)
def test_mix_of_a_head_count(heads: HeadCount, expected: Mix) -> None:
    assert mix_of(heads) == expected


@pytest.mark.parametrize(
    "heads",
    [
        HeadCount(specialized_fulltime_staff=2, supported_fulltime_borrowed=5, masters=1),
        HeadCount(specialized_parttime=7, supported_parttime=3, masters=9),
        HeadCount(supported_fulltime_staff=1),
    ],
)
def test_each_pair_adds_up_to_100(heads: HeadCount) -> None:
    mix = mix_of(heads)

    assert mix.specialized + mix.supported == 100
    assert mix.fulltime + mix.parttime == 100
    assert mix.phds + mix.masters == 100


def test_a_report_measures_the_signed_teachers_counted_or_not() -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))

    contracts = [
        fulltime_staff(DENTISTRY),
        fulltime_borrowed(BIOLOGY),
        parttime(DENTISTRY),
        parttime(DENTISTRY),  # beyond the specialized fulltime: signed, not counted
        master(DENTISTRY),
    ]

    report = evaluate_faculty(dentistry, contracts)

    assert len(report.counted_contracts) < len(report.included)
    assert report.mix == mix_of(report.signed)
    assert report.mix.specialized == Fraction(75)
    assert report.mix.parttime == Fraction(50)
    assert report.mix.masters == Fraction(20)
