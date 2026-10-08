"""Re-sign contracts to the faculties where they benefit the university most.

Employment terms (fulltime / parttime, staff / borrowed) never change; only the
faculty of each contract does. A contract may end up unsigned when every faculty
would either not count it or break a rule because of it. A contract locked into its
faculty (`Contract.is_locked`, once signed) is never moved.

"Better" depends on the `Strategy` (see strategies.py); all of them put compliance
first, then every faculty's target students. The default, MAXIMIZE_STUDENTS, goes for
the most students the ministry allows.

Search:
  1. Build two starting placements: the current one, and one by fit
     (each contract where its specialization is specialized).
  2. Improve each by moving one contract at a time while the strategy's key improves.
  3. Keep the best.

Two starts matter because share rules make a faculty worthless until enough of its
specializations are present, which one-contract moves cannot build alone.

Where each step lives:
  score.py       what one faculty contributes (adds up across faculties)
  outcome.py     a whole placement: totals, chapter max, moves
  strategies.py  what "better" means: one key per strategy
  placement.py   who goes first, which faculties fit a contract, and who could move
                 in its place (`substitutes_for`)
  board.py       the working state: place, move, compare, improve
  starts.py      the two starting placements
  search.py      `optimize`: starts -> improve -> best
"""

from unicap.domain.optimizer.outcome import Outcome, outcome_of
from unicap.domain.optimizer.placement import substitutes_for
from unicap.domain.optimizer.score import Score
from unicap.domain.optimizer.search import optimize
from unicap.domain.optimizer.strategies import Strategy

__all__ = ["Outcome", "Score", "Strategy", "optimize", "outcome_of", "substitutes_for"]
