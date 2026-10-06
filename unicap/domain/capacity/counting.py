"""Rules 1-4: which contracts the ministry counts.

Left out before counting (never counted, never a limit for anyone):
  - inactive contracts (or of an inactive employee / specialization)
  - contracts of employees who cannot be counted in this faculty (their excluded faculties)
  - contracts whose specialization the faculty does not accept
  - masters of a specialization whose faculty row does not calculate masters (excluded)
  - contracts of a type the specialization's row does not count here (`contract_type`)

Then every max is applied together until none drops anyone (a fixpoint), so every one of
them holds on the counted teachers at the end, whatever order they bite in:
  - parttime PhDs of a type: up to the counted fulltime PhDs of that type
  - masters: up to the counted specialized fulltime PhDs
  - a specialization's max share: its teachers (PhDs and masters, one head each) up to
    its max % of all counted teachers, rounded the faculty's `max_share_rounding` way
  - a specialization's max_teachers: its teachers (PhDs and masters) up to it
  - the faculty's max specialized / max supported: its PhDs of that type up to it

Rules feed each other (dropping a fulltime lowers the parttime and masters limits,
dropping anyone lowers every share limit), hence the fixpoint. Inside a group the cheapest
go first: masters, then parttime, then borrowed, staff last; among equals, the contracts
signed last.
"""

from collections.abc import Callable, Sequence

from unicap.domain.capacity.lookups import accepts, is_specialized, may_count, type_of
from unicap.domain.enums import ContractStatus
from unicap.domain.models import ChapterFaculty, Contract, Share
from unicap.domain.rounding import round_count
from unicap.domain.utils import as_fraction, count, group_by, partition

type Statuses = dict[Contract, ContractStatus]

type Rule = Callable[[ChapterFaculty, Sequence[Contract]], Statuses]


def count_contracts(faculty: ChapterFaculty, contracts: Sequence[Contract]) -> Statuses:
    """Status of every contract, in signing order (as the cards were dropped)."""
    included, inactive = partition(lambda c: c.is_included, contracts)

    allowed_here, barred = partition(lambda c: may_count(faculty, c), included)

    accepted, not_accepted = partition(lambda c: accepts(faculty, c), allowed_here)

    accepted, excluded_masters = partition(
        lambda c: c.is_phd or _share(faculty, c).calculate_masters, accepted
    )

    allowed, wrong_type = partition(lambda c: _share(faculty, c).allows(c.contract_type), accepted)

    uncounted = {
        **dict.fromkeys(inactive, ContractStatus.INACTIVE),
        **dict.fromkeys(barred, ContractStatus.FACULTY_NOT_ALLOWED),
        **dict.fromkeys(not_accepted, ContractStatus.SPECIALIZATION_NOT_ALLOWED),
        **dict.fromkeys(excluded_masters, ContractStatus.MASTERS_EXCLUDED),
        **dict.fromkeys(wrong_type, ContractStatus.CONTRACT_TYPE_NOT_ALLOWED),
        **overflowing(faculty, allowed),
    }

    return {c: uncounted.get(c, ContractStatus.COUNTED) for c in contracts}


def overflowing(faculty: ChapterFaculty, teachers: Sequence[Contract]) -> Statuses:
    """Apply every max until none drops anyone: what is left meets all of them."""
    uncounted: Statuses = {}

    while True:
        counted = [c for c in teachers if c not in uncounted]

        dropped = next((d for rule in RULES if (d := rule(faculty, counted))), None)

        if not dropped:
            return uncounted

        uncounted |= dropped


def parttime_overflow(faculty: ChapterFaculty, counted: Sequence[Contract]) -> Statuses:
    """Parttime PhDs of a type beyond the fulltime PhDs of that type."""
    dropped: list[Contract] = []

    phds = [c for c in counted if c.is_phd]

    for group in group_by(phds, lambda c: type_of(faculty, c)).values():
        fulltime, parttime = partition(lambda c: c.is_fulltime, group)

        dropped += parttime[len(fulltime) :]

    return dict.fromkeys(dropped, ContractStatus.PARTTIME_OVERFLOW)


def masters_overflow(faculty: ChapterFaculty, counted: Sequence[Contract]) -> Statuses:
    """Masters beyond the counted specialized fulltime PhDs."""
    limit = count(counted, lambda c: c.is_phd and c.is_fulltime and is_specialized(faculty, c))

    masters = [c for c in counted if not c.is_phd]

    return dict.fromkeys(masters[limit:], ContractStatus.MASTERS_OVERFLOW)


def share_overflow(faculty: ChapterFaculty, counted: Sequence[Contract]) -> Statuses:
    """A specialization beyond its max share of all counted teachers."""
    dropped: list[Contract] = []

    for specialization, group in group_by(counted, lambda c: c.employee.specialization).items():
        limit = max_share(faculty, faculty.share_of(specialization).upper_bound, len(counted))

        dropped += _cheapest_last(group)[limit:]

    return dict.fromkeys(dropped, ContractStatus.SHARE_OVERFLOW)


def teachers_overflow(faculty: ChapterFaculty, counted: Sequence[Contract]) -> Statuses:
    """A specialization's teachers (PhDs and masters) beyond its max_teachers."""
    dropped: list[Contract] = []

    for specialization, group in group_by(counted, lambda c: c.employee.specialization).items():
        limit = faculty.share_of(specialization).max_teachers

        if limit is not None:
            dropped += _cheapest_last(group)[limit:]

    return dict.fromkeys(dropped, ContractStatus.TEACHERS_OVERFLOW)


def type_overflow(faculty: ChapterFaculty, counted: Sequence[Contract]) -> Statuses:
    """PhDs beyond the faculty's max specialized / supported."""
    dropped: list[Contract] = []

    phds = [c for c in counted if c.is_phd]

    for kind, group in group_by(phds, lambda c: type_of(faculty, c)).items():
        _, limit = faculty.teachers_of_type(kind)

        if limit is not None:
            dropped += _cheapest_last(group)[limit:]

    return dict.fromkeys(dropped, ContractStatus.TYPE_OVERFLOW)


def max_share(faculty: ChapterFaculty, percentage: float, total: int) -> int:
    """The most teachers a `percentage` of `total` allows, rounded the faculty's way."""
    if percentage >= 100:
        return total

    return round_count(total * as_fraction(percentage) / 100, faculty.max_share_rounding)


# the order the maxes are tried in, each until it drops no one
RULES: tuple[Rule, ...] = (
    parttime_overflow,
    masters_overflow,
    share_overflow,
    teachers_overflow,
    type_overflow,
)


def _cheapest_last(group: Sequence[Contract]) -> list[Contract]:
    """Fulltime staff PhDs first, then borrowed, parttime, masters (stable: signing order)."""
    return sorted(group, key=lambda c: (not c.is_phd, not c.is_fulltime, not c.is_staff))


def _share(faculty: ChapterFaculty, contract: Contract) -> Share:
    return faculty.share_of(contract.employee.specialization)
