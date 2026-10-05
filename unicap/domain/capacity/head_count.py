"""The seven head counts of a faculty, and what its masters are worth in PhDs."""

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from unicap.domain.capacity.roster import Roster, roster_of
from unicap.domain.enums import SpecializationType
from unicap.domain.models import ChapterFaculty, Contract
from unicap.domain.rounding import round_count


@dataclass(frozen=True, slots=True)
class HeadCount:
    specialized_fulltime_staff: int = 0
    supported_fulltime_staff: int = 0
    specialized_fulltime_borrowed: int = 0
    supported_fulltime_borrowed: int = 0
    specialized_parttime: int = 0
    supported_parttime: int = 0
    masters: int = 0
    masters_as_phds: int = 0  # the masters in whole PhDs (see `masters_as_phds`)

    @property
    def specialized_fulltime(self) -> int:
        return self.specialized_fulltime_staff + self.specialized_fulltime_borrowed

    @property
    def supported_fulltime(self) -> int:
        return self.supported_fulltime_staff + self.supported_fulltime_borrowed

    @property
    def phds(self) -> int:
        parttime = self.specialized_parttime + self.supported_parttime

        return self.specialized_fulltime + self.supported_fulltime + parttime

    @property
    def phd_equivalents(self) -> int:
        """PhDs plus the masters' worth in PhDs (by default two masters = one PhD)."""
        return self.phds + self.masters_as_phds


def head_count(faculty: ChapterFaculty, contracts: Iterable[Contract]) -> HeadCount:
    """Count only contracts whose specialization the faculty accepts."""
    return head_count_of(faculty, roster_of(faculty, contracts))


def masters_as_phds(faculty: ChapterFaculty, roster: Roster) -> int:
    """The faculty's masters in whole PhDs.

    Each specialization's masters count by its own `masters_per_phd`; their sum is rounded
    once, the faculty's `masters_rounding` way (one master of two specializations each,
    two a PhD: one PhD, not two halves rounded away).
    """
    worth = sum(
        (
            Fraction(item.masters, faculty.share_of(item.specialization).masters_per_phd)
            for item in roster.counts
        ),
        Fraction(0),
    )

    return round_count(worth, faculty.masters_rounding)


def head_count_of(faculty: ChapterFaculty, roster: Roster) -> HeadCount:
    """The seven head counts of a roster, by the faculty's specialized / supported."""

    def total(kind: SpecializationType, field: str) -> int:
        return sum(
            getattr(item, field)
            for item in roster.counts
            if faculty.type_of(item.specialization) is kind
        )

    specialized, supported = SpecializationType.SPECIALIZED, SpecializationType.SUPPORTED

    return HeadCount(
        specialized_fulltime_staff=total(specialized, "fulltime_staff"),
        supported_fulltime_staff=total(supported, "fulltime_staff"),
        specialized_fulltime_borrowed=total(specialized, "fulltime_borrowed"),
        supported_fulltime_borrowed=total(supported, "fulltime_borrowed"),
        specialized_parttime=total(specialized, "parttime"),
        supported_parttime=total(supported, "parttime"),
        masters=roster.masters,
        masters_as_phds=masters_as_phds(faculty, roster),
    )
