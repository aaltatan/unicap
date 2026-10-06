"""Rounding a calculated number of people to a whole one.

Every rounded value here is a count (teachers, PhD equivalents), so it always rounds to a
whole number (0 decimal places); only how it rounds is a choice:

  FLOOR      down:              1.9 -> 1
  CEILING    up:                1.1 -> 2
  HALF_UP    mathematical:      1.5 -> 2, 1.4 -> 1
  HALF_DOWN  halves go down:    1.5 -> 1, 1.6 -> 2
  HALF_EVEN  banker's:          1.5 -> 2, 2.5 -> 2

Example:
    >>> from fractions import Fraction
    >>> round_count(Fraction(3, 2), RoundingMode.FLOOR)
    1
    >>> round_count(Fraction(3, 2), RoundingMode.HALF_UP)
    2
"""

from enum import StrEnum, auto
from fractions import Fraction
from math import ceil, floor

HALF = Fraction(1, 2)


class RoundingMode(StrEnum):
    FLOOR = auto()
    CEILING = auto()
    HALF_UP = auto()
    HALF_DOWN = auto()
    HALF_EVEN = auto()


def round_count(value: Fraction | int, mode: RoundingMode) -> int:
    """Round a (non-negative) calculated count to a whole number, the `mode` way.

    Example:
        >>> round_count(Fraction(5, 2), RoundingMode.HALF_EVEN)
        2
        >>> round_count(Fraction(1, 10), RoundingMode.CEILING)
        1
    """
    value = Fraction(value)

    match mode:
        case RoundingMode.FLOOR:
            return floor(value)
        case RoundingMode.CEILING:
            return ceil(value)
        case RoundingMode.HALF_UP:
            return floor(value + HALF)
        case RoundingMode.HALF_DOWN:
            return ceil(value - HALF)
        case RoundingMode.HALF_EVEN:
            return round(value)
