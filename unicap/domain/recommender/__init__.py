"""Recommend the contracts a university should sign to solve its problems.

A problem is a violation (a minimum missed, current students without a seat) and, when
asked, a faculty below its target students. The recommender adds new contracts to the
faculties as they are (it never moves anyone: the optimizer does that) and tells how many
of which kind, specialization and faculty solve the most.

Strategies decide which helping contract comes first (strategies.py): the fewest
contracts, low salaries, fulltime staff first, borrowed first, or specialized first. The
kinds the university is willing to sign (`HireKind`) can be limited.

Where each step lives:
  hires.py       what can be signed: `HireKind`, and the result's `Hire`
  gap.py         how far a faculty is from having no problem, in teachers
  strategies.py  which helping contract comes first
  search.py      `recommend`: the greedy search, faculty by faculty
"""

from unicap.domain.recommender.hires import ALL_KINDS, Hire, HireKind
from unicap.domain.recommender.search import Recommendation, recommend
from unicap.domain.recommender.strategies import RecommendationStrategy

__all__ = ["ALL_KINDS", "Hire", "HireKind", "Recommendation", "RecommendationStrategy", "recommend"]
