"""Staff are listed by kind, the head counts' order; signing order among equals."""

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
from unicap.domain import evaluate_faculty, in_staff_order


def test_signed_staff_in_head_count_order() -> None:
    dentistry = faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))

    signed = {
        "master": master(DENTISTRY, dentistry),
        "supported parttime": parttime(BIOLOGY, dentistry),
        "supported borrowed": fulltime_borrowed(BIOLOGY, dentistry),
        "supported staff": fulltime_staff(BIOLOGY, dentistry),
        "specialized parttime": parttime(DENTISTRY, dentistry),
        "specialized borrowed": fulltime_borrowed(DENTISTRY, dentistry),
        "specialized staff": fulltime_staff(DENTISTRY, dentistry),
    }
    names = {contract: name for name, contract in signed.items()}

    report = evaluate_faculty(dentistry, list(signed.values()))

    assert [names[contract] for contract, _ in report.in_staff_order] == [
        "specialized staff",
        "specialized borrowed",
        "specialized parttime",
        "supported staff",
        "supported borrowed",
        "supported parttime",
        "master",
    ]


def test_signing_order_among_equals() -> None:
    first, second = fulltime_staff(DENTISTRY), fulltime_staff(DENTISTRY)

    assert in_staff_order([parttime(DENTISTRY), first, second])[:2] == [first, second]


def test_unsigned_have_no_specialized_or_supported_yet() -> None:
    supported_staff, specialized_borrowed = fulltime_staff(BIOLOGY), fulltime_borrowed(DENTISTRY)

    assert in_staff_order([specialized_borrowed, supported_staff]) == [
        supported_staff,
        specialized_borrowed,
    ]
