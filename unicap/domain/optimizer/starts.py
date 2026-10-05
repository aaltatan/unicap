"""The two starting placements the search improves on."""

from unicap.domain.models import Chapter
from unicap.domain.optimizer.board import Board
from unicap.domain.optimizer.placement import accepting, placement_priority, specialized_in
from unicap.domain.optimizer.strategies import Strategy
from unicap.domain.utils import partition


def start_as_signed(chapter: Chapter, strategy: Strategy) -> Board:
    """Keep the current placement and only place the unsigned contracts."""
    board = Board(chapter, strategy)

    faculties = board.faculties

    signed, unsigned = partition(
        lambda c: c.faculty in faculties or not board.is_calculated(c), chapter.contracts
    )

    for contract in signed:
        board.move(contract, contract.faculty if contract.faculty in faculties else None)

    for contract in sorted(unsigned, key=placement_priority):
        board.move(contract, board.best_faculty(contract, accepting(faculties, contract)))

    return board


def start_by_fit(chapter: Chapter, strategy: Strategy) -> Board:
    """Sign each contract where its specialization is specialized, the rest where they add most."""
    board = Board(chapter, strategy)

    faculties = board.faculties

    specialized_first = sorted(
        chapter.contracts,
        key=lambda c: (not specialized_in(faculties, c), placement_priority(c)),
    )

    for contract in specialized_first:
        if not board.is_calculated(contract):  # left out: stays where it is
            board.move(contract, contract.faculty if contract.faculty in faculties else None)

            continue

        preferred = specialized_in(faculties, contract) or accepting(faculties, contract)

        board.move(contract, board.best_faculty(contract, preferred))

    return board


def start_from(chapter: Chapter, placement: Chapter, strategy: Strategy) -> Board:
    """Start from another placement (e.g. another strategy's result).

    Moves are still counted from `chapter`, the placement the user has now.
    """
    board = Board(chapter, strategy)

    faculties = board.faculties

    for contract in placement.contracts:
        board.move(contract, contract.faculty if contract.faculty in faculties else None)

    return board
