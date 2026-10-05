"""`optimize`: build the starts, improve each, keep the best for the strategy."""

from unicap.domain.models import Chapter
from unicap.domain.optimizer.starts import start_as_signed, start_by_fit, start_from
from unicap.domain.optimizer.strategies import Strategy

DEFAULT = Strategy.MAXIMIZE_STUDENTS


def optimize(
    chapter: Chapter,
    strategy: Strategy = DEFAULT,
    max_rounds: int = 20,
) -> Chapter:
    """Re-sign contracts among the chapter's faculties for `strategy`.

    Every strategy puts compliance first; the others also start from the default's
    result, so none ends up less compliant.
    """
    boards = [start_as_signed(chapter, strategy), start_by_fit(chapter, strategy)]

    if strategy is not DEFAULT:
        default = optimize(chapter, DEFAULT, max_rounds)

        boards.append(start_from(chapter, default, strategy))

    for board in boards:
        board.improve(max_rounds)

    best = max(boards, key=lambda board: board.key())

    return chapter.with_contracts(
        contract.signed_to(best.faculty_of[contract.employee]) for contract in chapter.contracts
    )
