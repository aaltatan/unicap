"""Field validators."""

from django.core.exceptions import ValidationError
from django.core.files import File

from .reports import ReportTemplateError, check


def validate_docx_template(file: File) -> None:
    """An uploaded report template: a .docx whose docxtpl (Jinja) tags are valid.

    Raises:
        ValidationError: with the reason, so the admin can fix the file.
    """
    file.seek(0)

    try:
        check(file)
    except ReportTemplateError as error:
        raise ValidationError(str(error), code="invalid_template") from error
    finally:
        file.seek(0)
