"""Shared form widgets."""

from typing import Any

from django import forms


class NumberInput(forms.NumberInput):
    """A number input showing floats without useless decimals: 60.0 -> "60", 12.5 -> "12.5"."""

    def __init__(self, attrs: dict[str, Any] | None = None) -> None:
        """Any step, so decimals are accepted."""
        super().__init__({"step": "any", **(attrs or {})})

    def format_value(self, value: Any) -> str | None:  # noqa: ANN401 - Django's hook
        """The value as the input shows it."""
        if value in (None, ""):
            return None

        try:
            return f"{float(value):g}"
        except (TypeError, ValueError):
            return str(value)
