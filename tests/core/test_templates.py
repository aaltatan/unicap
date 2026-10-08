"""Guards on the templates themselves: pitfalls that fail silently when a page is drawn."""

import re
from pathlib import Path

from django.conf import settings

TEMPLATES = Path(settings.BASE_DIR) / "templates"

# `<c-tag :width="size|default:'lg'">`: django-cotton cannot resolve a filter inside a dynamic
# attribute and passes nothing, without an error. Compute the value first
# (`{% with size=... %}`), or pass it as text: `width="{{ size|default:'lg' }}"`.
FILTER_IN_DYNAMIC_ATTRIBUTE = re.compile(
    r"""<c-[\w.-]+[^>]*?\s:[\w-]+="[^"{]*\|[^"]*\"""", re.DOTALL
)


def offenders(text: str) -> list[str]:
    return [match.group(0)[-80:] for match in FILTER_IN_DYNAMIC_ATTRIBUTE.finditer(text)]


def test_the_guard_sees_a_filter_in_a_dynamic_attribute() -> None:
    assert offenders("""<c-modal :width="size|default:'lg'">""")
    assert offenders("""<c-type-tag class="x"\n  :kind="contract|specialization_type" />""")
    assert not offenders("""<c-modal width="{{ size|default:'lg' }}" :title="page_title">""")
    assert not offenders("""<c-field :field="field" class="{% if a|length %}x{% endif %}" />""")


def test_no_component_is_given_a_filtered_dynamic_attribute() -> None:
    found = {
        str(path.relative_to(TEMPLATES)): hits
        for path in TEMPLATES.rglob("*.html")
        if (hits := offenders(path.read_text(encoding="utf-8")))
    }

    assert not found


def test_fulltime_is_said_one_way_in_arabic() -> None:
    """`كلي`, everywhere: the catalog holds no other word for it."""
    import polib  # noqa: PLC0415
    from django.conf import settings  # noqa: PLC0415

    catalog = polib.pofile(str(settings.BASE_DIR / "locale" / "ar" / "LC_MESSAGES" / "django.po"))

    texts = {
        entry.msgid: " ".join([entry.msgstr, *entry.msgstr_plural.values()])
        for entry in catalog
        if not entry.obsolete
    }

    assert not [msgid for msgid, text in texts.items() if "متفرغ" in text]
    assert texts["fulltime"] == "كلي"
    assert texts["FT staff"] == "كلي ملاك"
    assert all("كلي" in text for msgid, text in texts.items() if "fulltime" in msgid.lower())
