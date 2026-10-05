"""A faculty's teachers as percentages: what its signed staff is made of.

Read beside the staff percentage (`violations.staff_percentage`), and like it measured on
the teachers signed to the faculty (the ones in the calculation), counted or not:

  specialized / supported   of its PhDs
  fulltime / parttime       of its PhDs
  PhDs / masters            of all its teachers (heads)

Each pair adds up to 100; a faculty with nobody to measure has 0 in both.

Example:
    >>> mix = mix_of(HeadCount(specialized_fulltime_staff=3, supported_parttime=1, masters=4))
    >>> mix.specialized, mix.parttime, mix.masters
    (Fraction(75, 1), Fraction(25, 1), Fraction(50, 1))
"""

from dataclasses import dataclass
from fractions import Fraction

from unicap.domain.capacity.head_count import HeadCount


@dataclass(frozen=True, slots=True)
class Mix:
    """Percentages (0-100) of a faculty's teachers, by type, contract and degree."""

    specialized: Fraction = Fraction(0)
    supported: Fraction = Fraction(0)
    fulltime: Fraction = Fraction(0)
    parttime: Fraction = Fraction(0)
    phds: Fraction = Fraction(0)
    masters: Fraction = Fraction(0)


def mix_of(heads: HeadCount) -> Mix:
    """The mix of a head count (a faculty's signed teachers)."""
    specialized = heads.specialized_fulltime + heads.specialized_parttime
    fulltime = heads.specialized_fulltime + heads.supported_fulltime

    return Mix(
        specialized=_share(specialized, heads.phds),
        supported=_share(heads.phds - specialized, heads.phds),
        fulltime=_share(fulltime, heads.phds),
        parttime=_share(heads.phds - fulltime, heads.phds),
        phds=_share(heads.phds, heads.phds + heads.masters),
        masters=_share(heads.masters, heads.phds + heads.masters),
    )


def _share(part: int, whole: int) -> Fraction:
    return Fraction(part * 100, whole) if whole else Fraction(0)
