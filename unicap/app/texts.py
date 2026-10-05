"""The domain's messages in the user's language: its errors and its violations.

The domain writes them in English and also gives their `code` / `kind` and `params`; these
pick the translated sentence and fill it. Anything without a sentence keeps its message.
"""

from collections.abc import Mapping
from fractions import Fraction
from typing import cast

from django.utils.translation import gettext as _

from unicap.domain import DomainError, SpecializationType, Violation

from .choices import (
    DOMAIN_ERROR_MESSAGES,
    FIELD_LABELS,
    VIOLATION_MESSAGES,
    SpecializationTypeChoices,
)


def error_text(error: Exception) -> str:
    """An error as a message for the user: a domain error translated, any other as it is.

    Example:
        ```python
        except (DomainError, UserError) as error:
            messages.error(request, error_text(error))
        ```
    """
    if not isinstance(error, DomainError) or error.code is None:
        return str(error)

    params = dict(error.params)

    if "fields" in params:
        names = cast("list[object]", params["fields"])
        params["fields"] = [str(FIELD_LABELS.get(str(name), name)) for name in names]

    return _fill(DOMAIN_ERROR_MESSAGES.get(error.code), params, fallback=str(error))


def violation_text(violation: Violation) -> str:
    """A violation as a sentence in the active language."""
    template = VIOLATION_MESSAGES.get(violation.kind)

    return _fill(template, violation.params, fallback=violation.message)


def _fill(template: object, params: Mapping[str, object], *, fallback: str) -> str:
    if template is None or not params:
        return fallback

    try:
        return str(template) % {key: _param(value) for key, value in params.items()}
    except (KeyError, ValueError, TypeError):
        return fallback


def _param(value: object) -> object:
    """Names joined, percentages with one decimal, other numbers bare, types labelled."""
    if isinstance(value, SpecializationType):
        return str(SpecializationTypeChoices(value.value).label)

    if isinstance(value, (list, tuple, set, frozenset)):
        return _(", ").join(str(item) for item in value)  # Arabic: "، "

    if isinstance(value, Fraction):
        return f"{float(value):.1f}"

    if isinstance(value, float):
        return f"{value:g}"

    return value
