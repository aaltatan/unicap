"""The order staff are listed in: the head counts' order, signing order among equals.

  specialized fulltime staff, specialized fulltime borrowed, specialized parttime,
  supported fulltime staff, supported fulltime borrowed, supported parttime, masters

Only how lists read (cards, printed staff): counting keeps the signing order.

Example:
    ```python
    in_staff_order(report.statuses, faculty)  # or sorted(..., key=staff_order)
    ```
"""

from collections.abc import Iterable

from unicap.domain.enums import SpecializationType
from unicap.domain.models import Contract, Faculty


def staff_order(contract: Contract, faculty: Faculty | None = None) -> tuple[bool, ...]:
    """Sort key: PhDs, specialized (in `faculty`), fulltime, staff first.

    Unsigned (`faculty` None), specialized / supported is not known yet: the rest decide.
    A specialization the faculty does not accept sorts with the supported.
    """
    specialization = contract.employee.specialization

    supported = faculty is not None and not (
        faculty.accepts(specialization)
        and faculty.type_of(specialization) is SpecializationType.SPECIALIZED
    )

    return not contract.is_phd, supported, not contract.is_fulltime, not contract.is_staff


def in_staff_order(contracts: Iterable[Contract], faculty: Faculty | None = None) -> list[Contract]:
    """`contracts` in `staff_order` (stable: signing order among equals)."""
    return sorted(contracts, key=lambda contract: staff_order(contract, faculty))
