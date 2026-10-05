"""Domain errors shown in the user's language, from their code and params."""

import pytest
from django.utils import translation

from unicap.app.choices import DOMAIN_ERROR_MESSAGES
from unicap.app.exceptions import UserError
from unicap.app.texts import error_text
from unicap.domain import Contract as DomainContract
from unicap.domain import (
    ContractType,
    DomainError,
    Employee,
    EmploymentType,
    ErrorCode,
    Specialization,
)

SAMI = Employee(1, "Dr. Sami", Specialization("Biology"))


def parttime_staff() -> DomainError:
    with pytest.raises(DomainError) as error:
        DomainContract(SAMI, ContractType.PARTTIME, EmploymentType.STAFF)
    return error.value


def test_the_domain_names_the_rule_and_its_values() -> None:
    error = parttime_staff()

    assert error.code is ErrorCode.PARTTIME_NOT_BORROWED
    assert error.params == {"employee": "Dr. Sami"}
    assert str(error) == "Dr. Sami: a parttime contract is always borrowed"


def test_every_rule_has_a_sentence() -> None:
    assert set(DOMAIN_ERROR_MESSAGES) == set(ErrorCode)


def test_in_english_the_message_reads_the_same() -> None:
    with translation.override("en"):
        assert error_text(parttime_staff()) == str(parttime_staff())


def test_in_arabic_the_message_is_translated_with_its_values() -> None:
    with translation.override("ar"):
        text = error_text(parttime_staff())

    assert text.startswith("Dr. Sami: ")
    assert "parttime" not in text


def test_names_and_fields_are_listed_in_the_language() -> None:
    error = DomainError(
        "Fall: x, y cannot be negative",
        ErrorCode.NEGATIVE,
        {"owner": "Fall", "fields": ["max_students", "current_students"]},
    )

    with translation.override("ar"):
        text = error_text(error)
        expected = translation.gettext("max students")

    assert expected in text
    assert "max_students" not in text
    assert "، " in text  # the Arabic comma between them


@pytest.mark.parametrize(
    "error",
    [
        DomainError("an error without a code"),
        UserError("a user error"),
        ValueError("anything else"),
    ],
)
def test_other_errors_keep_their_message(error: Exception) -> None:
    with translation.override("ar"):
        assert error_text(error) == str(error)
