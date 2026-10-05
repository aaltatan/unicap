import pytest

from tests.domain.factories import (
    BIOLOGY,
    DENTISTRY,
    MEDICINE,
    PHARMACY,
    faculty,
    specialized,
    supported,
)
from unicap.domain import ChapterFaculty


@pytest.fixture
def dentistry() -> ChapterFaculty:
    """New method: no shares, only specialized / supported."""
    return faculty("Dentistry", specialized(DENTISTRY), supported(BIOLOGY))


@pytest.fixture
def dentistry_with_shares() -> ChapterFaculty:
    """Old method: 60% dentistry, 20% biology, 20% medicine."""
    return faculty(
        "Dentistry",
        specialized(DENTISTRY, percentage=60, min_percentage=50, max_percentage=60),
        supported(BIOLOGY, percentage=20, min_percentage=15, max_percentage=25),
        supported(MEDICINE, percentage=20, min_percentage=15, max_percentage=25),
    )


@pytest.fixture
def pharmacy() -> ChapterFaculty:
    return faculty("Pharmacy", specialized(PHARMACY), supported(BIOLOGY))
