from collections.abc import Callable, Iterable
from fractions import Fraction
from math import floor

type Percentage = int | float


def partition[T](predicate: Callable[[T], bool], items: Iterable[T]) -> tuple[list[T], list[T]]:
    """Split items into (matching, not_matching), keeping the original order."""
    matching: list[T] = []
    not_matching: list[T] = []
    for item in items:
        (matching if predicate(item) else not_matching).append(item)
    return matching, not_matching


def group_by[T, K](items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    groups: dict[K, list[T]] = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return groups


def count[T](items: Iterable[T], predicate: Callable[[T], bool]) -> int:
    return sum(1 for item in items if predicate(item))


def as_fraction(percentage: Percentage) -> Fraction:
    """Exact value of a percentage (going through str avoids float noise: 0.29 -> 29/100)."""
    return Fraction(str(percentage))


def percent_of(part: int, whole: int) -> Fraction:
    return Fraction(part * 100, whole) if whole else Fraction(100)


def share_cap(total: int, percentage: Percentage) -> int:
    """Largest head count that stays within `percentage` of `total`."""
    return floor(total * as_fraction(percentage) / 100)
