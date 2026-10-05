# ruff: noqa: S311 - seeded randomness generates test cases, nothing secret
"""Every max holds on what is counted, every min is reported: checked on random faculties.

The checks recount from the statuses on their own (not with the rules' helpers), so a rule
that forgets a group, or bites before another one changes the totals, shows up here.
"""

import random
from collections import Counter
from fractions import Fraction
from math import ceil, floor

import pytest

from unicap.domain import (
    ChapterFaculty,
    Contract,
    ContractStatus,
    ContractType,
    Degree,
    Employee,
    EmploymentType,
    Faculty,
    RoundingMode,
    Share,
    Specialization,
    SpecializationType,
    ViolationKind,
    evaluate_faculty,
    round_count,
)

SPECIALIZATIONS = [Specialization(name) for name in ("A", "B", "C", "D")]

SEEDS = range(400)


def random_faculty(rng: random.Random) -> ChapterFaculty:
    chosen = rng.sample(SPECIALIZATIONS, rng.randint(1, 4))
    cut = rng.randint(1, len(chosen))
    specialized, supported = tuple(chosen[:cut]), tuple(chosen[cut:])

    shares = []
    left = 100

    for specialization in chosen:
        low = rng.choice([None, rng.randint(0, 40)])
        high = rng.choice([None, rng.randint(low or 0, 100)])
        low_teachers = rng.choice([None, rng.randint(0, 3)])
        high_teachers = rng.choice([None, rng.randint(low_teachers or 0, 6)])
        percentage = None

        if low is not None and high is not None and rng.random() < 0.3 and high <= left:
            percentage = rng.randint(low, high)
            left -= percentage

        shares.append(
            Share(
                specialization,
                percentage=percentage,
                min_percentage=low,
                max_percentage=high,
                min_teachers=low_teachers,
                max_teachers=high_teachers,
                contract_type=rng.choice(
                    [None, None, ContractType.FULLTIME, ContractType.PARTTIME]
                ),
                calculate_masters=rng.random() > 0.2,
                masters_per_phd=rng.randint(1, 4),
            )
        )

    def bounds() -> tuple[int | None, int | None]:
        low = rng.choice([None, rng.randint(0, 4)])
        return low, rng.choice([None, rng.randint(low or 0, 8)])

    min_specialized, max_specialized = bounds()
    min_supported, max_supported = bounds()

    return ChapterFaculty(
        Faculty("F", specialized=specialized, supported=supported),
        students_per_phd=rng.randint(1, 30),
        min_staff_percentage=rng.choice([0, 25, 50, 75]),
        current_students=rng.choice([None, rng.randint(0, 300)]),
        max_students=rng.choice([None, rng.randint(0, 300)]),
        shares=tuple(shares),
        min_specialized=min_specialized,
        max_specialized=max_specialized,
        min_supported=min_supported,
        max_supported=max_supported,
        max_share_rounding=rng.choice(list(RoundingMode)),
        min_share_rounding=rng.choice(list(RoundingMode)),
        staff_rounding=rng.choice(list(RoundingMode)),
        masters_rounding=rng.choice(list(RoundingMode)),
    )


def random_contracts(rng: random.Random, faculty: ChapterFaculty) -> list[Contract]:
    contracts = []

    for number in range(rng.randint(0, 25)):
        specialization = rng.choice([*SPECIALIZATIONS, Specialization("Z", is_active=False)])
        kind = rng.choice(["ft-staff", "ft-borrowed", "pt", "master"])
        contract_type, employment_type, degree = {
            "ft-staff": (ContractType.FULLTIME, EmploymentType.STAFF, Degree.PHD),
            "ft-borrowed": (ContractType.FULLTIME, EmploymentType.BORROWED, Degree.PHD),
            "pt": (ContractType.PARTTIME, EmploymentType.BORROWED, Degree.PHD),
            "master": (ContractType.FULLTIME, EmploymentType.STAFF, Degree.MASTER),
        }[kind]

        contracts.append(
            Contract(
                Employee(number, f"e{number}", specialization, is_active=rng.random() > 0.05),
                contract_type,
                employment_type,
                faculty.faculty,
                degree=degree,
                is_active=rng.random() > 0.05,
            )
        )

    return contracts


@pytest.mark.parametrize("seed", SEEDS)
def test_every_max_holds_on_the_counted_teachers(seed: int) -> None:  # noqa: C901
    rng = random.Random(seed)
    faculty = random_faculty(rng)
    contracts = random_contracts(rng, faculty)

    report = evaluate_faculty(faculty, contracts)

    counted = [c for c, status in report.statuses.items() if status.is_counted]

    def kind(contract: Contract) -> SpecializationType:
        return faculty.type_of(contract.employee.specialization)

    for contract in counted:
        assert contract.is_included
        assert faculty.accepts(contract.employee.specialization)

        share = faculty.share_of(contract.employee.specialization)
        assert share.allows(contract.contract_type)

        if not contract.is_phd:
            assert share.calculate_masters

    phds = [c for c in counted if c.is_phd]
    masters_counted = [c for c in counted if not c.is_phd]

    # parttime of a type: up to the fulltime of that type
    for of_type in SpecializationType:
        fulltime = sum(1 for c in phds if kind(c) is of_type and c.is_fulltime)
        parttime = sum(1 for c in phds if kind(c) is of_type and not c.is_fulltime)
        assert parttime <= fulltime

        _, maximum = faculty.teachers_of_type(of_type)
        if maximum is not None:
            assert fulltime + parttime <= maximum

    # masters: up to the specialized fulltime PhDs
    specialized_fulltime = sum(
        1 for c in phds if c.is_fulltime and kind(c) is SpecializationType.SPECIALIZED
    )
    assert len(masters_counted) <= specialized_fulltime

    # every specialization's max teachers and max share, of every counted teacher
    heads = Counter(c.employee.specialization for c in counted)
    total = len(counted)

    for share in faculty.shares:
        mine = heads[share.specialization]

        if share.max_teachers is not None:
            assert mine <= share.max_teachers

        if share.upper_bound < 100:
            cap = round_count(total * share.upper_bound / 100, faculty.max_share_rounding)
            assert mine <= cap, (share, mine, total)

    # every min is reported, and only when missed
    kinds = [v.kind for v in report.violations]

    teachers_short = any(
        share.min_teachers is not None and heads[share.specialization] < share.min_teachers
        for share in faculty.shares
    )
    types_short = any(
        (low := faculty.teachers_of_type(of_type)[0]) is not None
        and sum(1 for c in phds if kind(c) is of_type) < low
        for of_type in SpecializationType
    )
    assert (ViolationKind.TOO_FEW_TEACHERS in kinds) == teachers_short
    assert (ViolationKind.TOO_FEW_OF_TYPE in kinds) == types_short

    # capacity: whole PhD equivalents x students per PhD, capped
    worth = sum(
        (
            Fraction(1, faculty.share_of(c.employee.specialization).masters_per_phd)
            for c in masters_counted
        ),
        Fraction(0),
    )
    equivalents = len(phds) + round_count(worth, faculty.masters_rounding)
    expected = equivalents * faculty.students_per_phd
    if faculty.max_students is not None:
        expected = min(expected, faculty.max_students)
    assert report.capacity == expected

    seats_short = (
        faculty.current_students is not None and faculty.current_students > report.capacity
    )
    assert (ViolationKind.CURRENT_STUDENTS_OVER_CAPACITY in kinds) == seats_short

    # staff: of every signed PhD (uncounted too), rounded the faculty's way
    signed_phds = [
        c for c, status in report.statuses.items() if c.is_phd and not status.is_excluded
    ]
    staff = sum(
        1
        for c in signed_phds
        if c.is_fulltime and c.is_staff and faculty.accepts(c.employee.specialization)
    )
    exact = len(signed_phds) * faculty.min_staff_percentage / 100
    required = {
        RoundingMode.FLOOR: floor(exact),
        RoundingMode.CEILING: ceil(exact),
    }.get(faculty.staff_rounding)

    if required is not None:
        assert (ViolationKind.STAFF_RATIO_TOO_LOW in kinds) == (staff < required)


@pytest.mark.parametrize("seed", range(50))
def test_counting_never_depends_on_an_excluded_contract(seed: int) -> None:
    """Switching a contract off only changes the faculty as if it was never there."""
    rng = random.Random(seed)
    faculty = random_faculty(rng)
    contracts = random_contracts(rng, faculty)

    report = evaluate_faculty(faculty, contracts)

    kept = [c for c in contracts if c.is_included]
    without = evaluate_faculty(faculty, kept)

    assert without.capacity == report.capacity
    kept_statuses = {c: s for c, s in report.statuses.items() if s is not ContractStatus.INACTIVE}
    assert kept_statuses == dict(without.statuses)
