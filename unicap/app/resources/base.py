"""Import / export building blocks: every file holds one chapter's rows, referenced by name.

A row whose name exists in the chapter is updated, a new one is added, nothing is deleted;
the whole file is saved in one validated transaction (`ChapterOwnedManager.import_rows`).

Files speak the user's language (`TranslatedResource`): headers, choices and yes / no are
exported translated, and an import reads them in any of the site's languages (or as the
plain column names and values), so a file exported in Arabic imports in English too.

A resource also writes a sample of the file it imports (`sample_dataset`): a few dummy
rows, and for each column filled from a list its values (`sample_options`).
"""

from collections.abc import Iterator, Sequence
from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db.models import BooleanField, Field, Model, QuerySet
from django.utils import translation
from django.utils.functional import Promise
from django.utils.translation import gettext as _
from import_export import fields, resources, widgets
from tablib import Dataset

SAMPLE_ROWS = 2

LIST_SEPARATOR = ";"  # between the names of a cell holding several rows


class ChapterForeignKeyWidget(widgets.ForeignKeyWidget):
    """A foreign key written as the related row's name, looked up in the resource's chapter."""

    def __init__(self, model: type[Model], field: str = "name", **kwargs: Any) -> None:
        super().__init__(model, field=field, **kwargs)
        self.chapter: Model | None = None

    def get_queryset(self, value: Any, row: Any, *args: Any, **kwargs: Any) -> QuerySet:
        return self.model.objects.filter(chapter=self.chapter)

    def names(self) -> list[str]:
        """The names a cell may hold: the chapter's rows."""
        rows = self.model.objects.filter(chapter=self.chapter).order_by(self.field)

        return [str(name) for name in rows.values_list(self.field, flat=True)]

    def clean(self, value: Any, row: Any = None, **kwargs: Any) -> Any:
        if value in (None, ""):
            return None

        try:
            return super().clean(value, row, **kwargs)
        except self.model.DoesNotExist as error:
            name = self.model._meta.verbose_name  # noqa: SLF001
            msg = f"no {name} named {value!r} in this chapter"
            raise ValueError(msg) from error


class ChapterManyToManyWidget(widgets.ManyToManyWidget):
    """Several rows of the resource's chapter, written as their names: `a; b`."""

    def __init__(self, model: type[Model], field: str = "name", **kwargs: Any) -> None:
        super().__init__(model, separator=LIST_SEPARATOR, field=field, **kwargs)
        self.chapter: Model | None = None

    def clean(self, value: Any, row: Any = None, **kwargs: Any) -> Any:
        names = [name.strip() for name in str(value or "").split(self.separator) if name.strip()]

        rows = self.model.objects.filter(chapter=self.chapter, **{f"{self.field}__in": names})

        if unknown := sorted(set(names) - {getattr(found, self.field) for found in rows}):
            name = self.model._meta.verbose_name  # noqa: SLF001
            msg = f"no {name} named {', '.join(map(repr, unknown))} in this chapter"
            raise ValueError(msg)

        return rows

    def render(self, value: Any, obj: Any = None, **kwargs: Any) -> str:
        if value is None:  # a row not saved yet has none
            return ""

        names = sorted(str(getattr(row, self.field)) for row in value.all())

        return f"{self.separator} ".join(names)


class TranslatedResource(resources.ModelResource):
    """Headers, choices and booleans in the user's language; any language on import.

    A column's header is its `labels` entry, else its model field's verbose name.
    A sample's cells are the column's `samples` (one per row), else made up from its field.
    """

    labels: ClassVar[dict[str, str | Promise]] = {}
    samples: ClassVar[dict[str, Sequence[Any]]] = {}

    def get_export_headers(self, selected_fields: Any = None) -> list[str]:
        return [self._label(field.column_name) for field in self.get_export_fields(selected_fields)]

    def export_field(self, field: fields.Field, instance: Model, **kwargs: Any) -> Any:
        model_field = self._model_field(field.column_name)

        if model_field is None or field.attribute is None:
            return super().export_field(field, instance, **kwargs)

        value = getattr(instance, field.attribute)

        if model_field.choices:
            return str(dict(model_field.flatchoices).get(value, value))

        if isinstance(model_field, BooleanField):
            return _("yes") if value else _("no")

        return super().export_field(field, instance, **kwargs)

    def before_import(self, dataset: Any, **kwargs: Any) -> None:
        """Rename translated headers back to the column names."""
        super().before_import(dataset, **kwargs)

        columns = dict(self._lookup(self._header_labels()))

        dataset.headers = [columns.get(_key(header), header) for header in dataset.headers or ()]

    def before_import_row(self, row: Any, **kwargs: Any) -> None:
        """Read translated choices and yes / no back as stored values."""
        super().before_import_row(row, **kwargs)

        for column, values in self._value_lookups().items():
            if column in row and (value := values.get(_key(row[column]))) is not None:
                row[column] = value

    def sample_columns(self) -> list[str]:
        """The columns of a file to import, in an export's order."""
        return [field.column_name for field in self.get_export_fields()]

    def sample_options(self) -> dict[str, list[str]]:
        """For each column filled from a list (a choice, yes / no, a row's name): its values.

        In the user's language, as an export writes them and an import reads them.
        """
        options = {field.column_name: self._options(field) for field in self.get_export_fields()}

        return {column: values for column, values in options.items() if values}

    def sample_dataset(self) -> Dataset:
        """A file to fill in then import: translated headers and a few dummy rows."""
        columns = self.sample_columns()
        options = self.sample_options()

        dataset = Dataset(headers=[self._label(column) for column in columns])

        for index in range(SAMPLE_ROWS):
            dataset.append([self.sample_value(column, index, options) for column in columns])

        return dataset

    def sample_value(self, column: str, index: int, options: dict[str, list[str]]) -> Any:
        """The dummy cell of `column` in the sample's row `index` (from 0)."""
        if values := self.samples.get(column) or options.get(column):
            return values[index % len(values)]

        model_field = self._model_field(column)

        if model_field is None or model_field.blank:
            return ""

        if model_field.has_default():
            return model_field.get_default()

        return f"{self._sample_name(column, model_field)} {index + 1}"

    def _options(self, field: fields.Field) -> list[str]:
        if isinstance(field.widget, ChapterForeignKeyWidget):
            return field.widget.names()

        model_field = self._model_field(field.column_name)

        if model_field is None or not _plain_values(model_field):
            return []

        return [str(label) for _value, label in _labels(model_field)]

    def _sample_name(self, column: str, model_field: Field) -> str:
        """What a made-up text cell names: the related row, this row, or the column."""
        if model_field.related_model is not None:
            return str(model_field.related_model._meta.verbose_name)  # noqa: SLF001

        if column in self.get_import_id_fields():
            return str(self._meta.model._meta.verbose_name)  # noqa: SLF001

        return str(model_field.verbose_name)

    def _label(self, column: str) -> str:
        if column in self.labels:
            return str(self.labels[column])

        model_field = self._model_field(column)

        return str(model_field.verbose_name) if model_field else column

    def _model_field(self, column: str) -> Any:
        try:
            return self._meta.model._meta.get_field(column)  # noqa: SLF001
        except FieldDoesNotExist:
            return None

    def _header_labels(self) -> Iterator[tuple[str, str]]:
        """(label, column) in every language, and (column, column)."""
        columns = [field.column_name for field in self.get_import_fields()]

        for column in columns:
            yield column, column

        for language, _name in settings.LANGUAGES:
            with translation.override(language):
                for column in columns:
                    yield self._label(column), column

    def _value_lookups(self) -> dict[str, dict[str, Any]]:
        """For each choice or yes / no column: every language's label -> the stored value."""
        lookups: dict[str, dict[str, Any]] = {}

        for field in self.get_import_fields():
            model_field = self._model_field(field.column_name)

            if model_field is None or not (pairs := _plain_values(model_field)):
                continue

            for language, _name in settings.LANGUAGES:
                with translation.override(language):
                    pairs += [(str(label), value) for value, label in _labels(model_field)]

            lookups[field.column_name] = dict(self._lookup(pairs))

        return lookups

    @staticmethod
    def _lookup(pairs: Any) -> Iterator[tuple[str, Any]]:
        for text, value in pairs:
            yield _key(text), value


def _plain_values(model_field: Any) -> list[tuple[str, Any]]:
    """A choice or yes / no column's untranslated values (none: the column is neither)."""
    if model_field.choices:
        return [(value, value) for value, _label in model_field.flatchoices]

    if isinstance(model_field, BooleanField):
        return [("1", True), ("0", False), ("true", True), ("false", False)]

    return []


def _labels(model_field: Any) -> list[tuple[Any, Any]]:
    """(value, label) of a choice or yes / no column, in the active language."""
    if model_field.choices:
        return list(model_field.flatchoices)

    return [(True, _("yes")), (False, _("no"))]


def _key(text: object) -> str:
    """Compare headers and values ignoring case and surrounding spaces."""
    return str(text).strip().casefold() if text is not None else ""


class ChapterResource(TranslatedResource):
    """A resource over one chapter's rows: lookups, foreign keys and new rows stay in it."""

    def __init__(self, *, chapter: Model | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.chapter = chapter

        for field in self.fields.values():
            if isinstance(field.widget, (ChapterForeignKeyWidget, ChapterManyToManyWidget)):
                field.widget.chapter = chapter

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(chapter=self.chapter)

    def init_instance(self, row: Any = None) -> Model:
        """A new row belongs to the chapter before it is validated."""
        instance = super().init_instance(row)
        instance.chapter = self.chapter
        return instance
