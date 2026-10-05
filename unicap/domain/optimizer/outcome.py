"""A whole placement, as the strategies compare it."""

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction

from unicap.domain.capacity import evaluate_faculty
from unicap.domain.capacity.students import capped
from unicap.domain.models import Chapter
from unicap.domain.optimizer.score import NO_SALARIES, Score
from unicap.domain.utils import percent_of


@dataclass(frozen=True, slots=True)
class Outcome:
    violations: int
    students: int  # capped by every faculty's max and by the chapter's max
    teachers: int  # counted contracts
    signed: int
    uncounted: int
    target_shortfall: int
    seat_shortage: int  # current students without a seat
    moves: int  # contracts whose faculty changed from the starting chapter
    teacher_shortage: int = 0  # PhDs missing to reach min_teachers
    staff_percentage: Fraction = Fraction(100)  # staff among every signed PhD
    lowest_staff_percentage: Fraction = Fraction(100)  # the weakest faculty's
    salaries: tuple[int, ...] = NO_SALARIES  # contracts per salary class, most expensive first

    @classmethod
    def of(
        cls,
        total: Score,
        chapter_max: int | None,
        moves: int,
        faculties: Iterable[Score] = (),
    ) -> "Outcome":
        """`faculties`: each faculty's score, for the weakest staff percentage."""
        ratios = [percent_of(s.staff, s.phds) for s in faculties if s.phds]

        overall = percent_of(total.staff, total.phds)

        return cls(
            violations=total.violations,
            students=capped(total.students, chapter_max),
            teachers=total.teachers,
            signed=total.signed,
            uncounted=total.uncounted,
            target_shortfall=total.target_shortfall,
            seat_shortage=total.seat_shortage,
            moves=moves,
            teacher_shortage=total.teacher_shortage,
            staff_percentage=overall,
            lowest_staff_percentage=min(ratios, default=overall),
            salaries=total.salaries,
        )

    @property
    def overflow_percentage(self) -> Fraction:
        """Uncounted among signed contracts, in percent (0 when nothing is signed)."""
        return Fraction(self.uncounted * 100, self.signed) if self.signed else Fraction(0)


def outcome_of(chapter: Chapter, origin: Chapter | None = None) -> Outcome:
    """Measure `chapter`, counting moves from `origin` (default: no moves)."""
    scores = [
        Score.of(evaluate_faculty(f, chapter.contracts_of(f.faculty))) for f in chapter.faculties
    ]

    origin_faculty = {c.employee: c.faculty for c in (origin or chapter).contracts}

    moves = sum(1 for c in chapter.contracts if origin_faculty.get(c.employee) != c.faculty)

    return Outcome.of(sum(scores, Score()), chapter.max_students, moves, scores)
