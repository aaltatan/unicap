"""Word documents from docx templates: docxtpl reads the .docx, Jinja2 fills its tags.

The tags are written in Word (`{{ chapter.name }}`, `{%tr for f in faculties %}`), by admins,
so they run in a sandboxed Jinja2 environment (no access to Python internals), autoescaped
so names holding `&` or `<` stay valid XML.
"""

from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import IO, Any
from zipfile import BadZipFile

from django.http import FileResponse
from django.utils.text import get_valid_filename
from django.utils.translation import gettext as _
from docx.opc.exceptions import PackageNotFoundError
from docxtpl import DocxTemplate
from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from ..exceptions import UserError
from .pdf import PDF_CONTENT_TYPE

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

CONTENT_TYPES = {"docx": DOCX_CONTENT_TYPE, "pdf": PDF_CONTENT_TYPE}

Source = str | Path | IO[bytes]

# what a broken file or tag raises: not a zip, not a Word package, bad Jinja, bad XML
_ERRORS = (BadZipFile, PackageNotFoundError, TemplateError, KeyError, ValueError, OSError)


def environment() -> SandboxedEnvironment:
    """The Jinja2 environment every report template is parsed and filled with."""
    return SandboxedEnvironment(autoescape=True)


class ReportTemplateError(UserError):
    """A docx template that cannot be read or rendered."""

    def __init__(self, error: Exception) -> None:
        """Name the underlying error, so the admin knows what to fix in the file."""
        msg = _("The Word template cannot be used: %(error)s") % {"error": error}
        super().__init__(msg)


def render(source: Source, context: Mapping[str, Any]) -> bytes:
    """Fill the template at `source` with `context` and return the .docx file's bytes.

    Raises:
        ReportTemplateError: the template is not a docx file, or its tags are invalid.

    Example:
        ```python
        content = render(path, {"chapter": {"name": "2026 / Fall"}})
        ```
    """
    try:
        document = DocxTemplate(source)
        document.render(dict(context), jinja_env=environment(), autoescape=True)
    except _ERRORS as error:
        raise ReportTemplateError(error) from error

    output = BytesIO()
    document.save(output)
    return output.getvalue()


def check(source: Source) -> None:
    """Parse the template without filling it: its Jinja tags must be valid.

    Raises:
        ReportTemplateError: the file is not a docx, or a tag is invalid.
    """
    try:
        DocxTemplate(source).get_undeclared_template_variables(jinja_env=environment())
    except _ERRORS as error:
        raise ReportTemplateError(error) from error


def attachment(content: bytes, *names: str, extension: str = "docx") -> FileResponse:
    """Download `content` as `<names joined by " - ">.<extension>` (`docx` or `pdf`)."""
    filename = f"{get_valid_filename(' - '.join(names))}.{extension}"

    return FileResponse(
        BytesIO(content),
        as_attachment=True,
        filename=filename,
        content_type=CONTENT_TYPES[extension],
    )
