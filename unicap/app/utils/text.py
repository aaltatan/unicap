# ruff: noqa: RUF001 - the Arabic letters are the point: their spelling variants
"""Text as searches compare it: case, Arabic diacritics and spelling variants ignored.

`normalize` (Python) and `Normalized` (the database) do the same, so a search term and a
stored name meet halfway: "إدارة" and "اداره" are the same word.
"""

from typing import TypeAlias

from django.db.models import Func, TextField, Value
from django.db.models.functions import Lower, Replace
from django.utils.functional import Promise

# letters written several ways -> one way
LETTERS = {
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ة": "ه",
    "ى": "ي",
    "ؤ": "و",
    "ئ": "ي",
}

# marks that do not change a word: Arabic diacritics and the tatweel
MARKS = (
    "ً",
    "ٌ",
    "ٍ",
    "َ",
    "ُ",
    "ِ",
    "ّ",
    "ْ",
    "ٰ",
    "ـ",
)

ARTICLES = ("وال", "بال", "فال", "كال", "لل", "ال")


def normalize(text: str) -> str:
    """Lowercase, without Arabic diacritics or spelling variants (as `Normalized` does).

    Example:
        >>> normalize("إدارةُ الأعمال") == normalize("اداره الاعمال")
        True
    """
    text = text.lower()

    for variant, letter in LETTERS.items():
        text = text.replace(variant, letter)

    for mark in MARKS:
        text = text.replace(mark, "")

    return text.strip()


def search_terms(value: str) -> list[str]:
    """The words of a search, normalized, a leading Arabic article dropped.

    "العمارة" then finds "عمارة" too; short words keep their letters.

    Example:
        >>> search_terms("هند  العمارة")
        ['هند', 'عماره']
    """
    terms = []

    for word in value.split():
        term = normalize(word)

        for article in ARTICLES:
            if term.startswith(article) and len(term) - len(article) >= 3:  # noqa: PLR2004
                term = term[len(article) :]
                break

        if term:
            terms.append(term)

    return terms


def Normalized(expression: str | Func) -> Func:  # noqa: N802 - reads like a db function
    """The database's side of `normalize`: `Normalized("name")` in a filter or annotation."""
    result: Func = Lower(expression, output_field=TextField())

    for variant, letter in LETTERS.items():
        result = Replace(result, Value(variant), Value(letter), output_field=TextField())

    for mark in MARKS:
        result = Replace(result, Value(mark), Value(""), output_field=TextField())

    return result


# a label: a plain string, or a lazy translation (`gettext_lazy`) rendered when shown
StrOrPromise: TypeAlias = str | Promise
