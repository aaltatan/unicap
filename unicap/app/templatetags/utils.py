"""Template helpers loaded in every template (a `builtins` library).

They only format or look up values the view already computed.
"""

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from django import template
from django.db.models import Model
from django.forms import ModelChoiceField
from django.http import HttpRequest, QueryDict
from django.utils.encoding import escape_uri_path

from ..utils import parse_ordering

register = template.Library()


@register.filter
def get_item(mapping: Mapping[Any, Any] | None, key: Any) -> Any:
    """`{{ themes|get_item:theme }}`: a mapping's value, or "" when missing."""
    if not mapping:
        return ""

    return mapping.get(key, mapping.get(str(key), ""))


@register.filter
def verbose_name(model: type[Model] | Model, field: str) -> str:
    """`{{ model|verbose_name:'name' }}`: a model field's (translated) verbose name."""
    return str(getattr(model._meta.get_field(field), "verbose_name", field))  # noqa: SLF001


@register.filter
def percent(value: float | Fraction | None, digits: int = 0) -> str:
    """`{{ report.staff_percentage|percent }}` -> "62%"; "" for None."""
    if value is None:
        return ""

    return f"{float(value):.{int(digits)}f}%"


@register.filter
def number(value: float | Fraction | None) -> str:
    """A number without useless decimals: 50.0 -> "50", 12.5 -> "12.5"; "" for None."""
    if value is None:
        return ""

    return f"{float(value):g}"


@register.simple_tag(takes_context=True)
def active_link(context: template.Context, path: str, css: str = "active") -> str:
    """`css` when the request's path is `path` or below it (the dashboard only on itself)."""
    request: HttpRequest | None = context.get("request")

    if request is None:
        return ""

    current = escape_uri_path(request.path)

    if path == "/":
        return css if current == "/" else ""

    return css if current.startswith(path) else ""


@register.simple_tag(takes_context=True)
def sort_state(context: template.Context, field: str) -> dict[str, Any]:
    """How a table column is sorted now, and the querystrings to sort it next.

    Click cycles the column alone: ascending -> descending -> off. Shift+click adds it
    (or cycles it) as another level, keeping the others.

    Returns:
        `{"direction": "asc" | "desc" | "", "level": 1.., "single": "?..", "multi": "?.."}`
    """
    request: HttpRequest = context["request"]

    ordering = parse_ordering(request.GET.get("ordering"))

    fields = [item.lstrip("-") for item in ordering]

    direction, level = "", 0

    if field in fields:
        level = fields.index(field) + 1
        direction = "desc" if ordering[level - 1].startswith("-") else "asc"

    following = {"": field, "asc": f"-{field}", "desc": ""}[direction]

    single = [following] if following else []

    multi = [item for item in ordering if item.lstrip("-") != field]

    if following:
        position = level - 1 if level else len(multi)
        multi.insert(position, following)

    return {
        "direction": direction,
        "level": level if len(ordering) > 1 else 0,
        "single": _with(request.GET, ordering=",".join(single)),
        "multi": _with(request.GET, ordering=",".join(multi)),
    }


@register.simple_tag(takes_context=True)
def page_query(context: template.Context, page: int) -> str:
    """The current querystring on another page."""
    return _with(context["request"].GET, page=str(page))


def _with(query: QueryDict, **changes: str) -> str:
    """The querystring with `changes` (an empty value drops the key; the page resets)."""
    updated = query.copy()

    updated.pop("page", None) if "page" not in changes else None

    for key, value in changes.items():
        if value:
            updated[key] = value
        else:
            updated.pop(key, None)

    encoded = updated.urlencode()

    return f"?{encoded}" if encoded else "?"


@register.filter
def widget_kind(field: Any) -> str:
    """How a form field is drawn: checkbox, checkboxes, radios, search, select, textarea, input.

    `search`: one row chosen among a model's rows (a select searched by typing).
    """
    widget = field.field.widget
    name = type(widget).__name__

    if name == "Select" and isinstance(field.field, ModelChoiceField):
        return "search"

    kinds = {
        "CheckboxInput": "checkbox",
        "CheckboxSelectMultiple": "checkboxes",
        "RadioSelect": "radios",
        "Select": "select",
        "SelectMultiple": "select",
        "NullBooleanSelect": "select",
        "Textarea": "textarea",
        "HiddenInput": "hidden",
    }

    return kinds.get(name, "input")
