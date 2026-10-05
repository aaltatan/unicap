"""Shared form behaviour."""

from typing import Any, cast

from django import forms
from django.db.models import Model, QuerySet


class ChapterOwnedForm(forms.ModelForm):
    """A form for a row of the current chapter: choices are limited to that chapter.

    `chapter_querysets` names the fields whose choices are the chapter's rows.
    """

    chapter_querysets: tuple[str, ...] = ()

    def __init__(self, *args: Any, chapter: Model | None = None, **kwargs: Any) -> None:
        """Bind the form to `chapter`: new rows belong to it, choices come from it."""
        super().__init__(*args, **kwargs)

        self.chapter = chapter

        if (
            chapter is not None
            and self.instance.pk is None
            and hasattr(self.instance, "chapter_id")
        ):
            self.instance.chapter = chapter

        for name in self.chapter_querysets:
            if name in self.fields:
                field = cast("forms.ModelChoiceField", self.fields[name])
                field.queryset = cast("QuerySet", field.queryset).filter(chapter=chapter)
