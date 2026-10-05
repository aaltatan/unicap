"""PDF files from the Word reports: the filled .docx, converted by an office suite.

A report is one admin-editable Word template, so its PDF is that document converted, not a
second layout. The conversion is done by LibreOffice (`soffice`, on any system: set
`SOFFICE_PATH` when it is not on the PATH) or, on Windows without it, by Microsoft Word.
"""

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext as _

from ..exceptions import UserError

PDF_CONTENT_TYPE = "application/pdf"

TIMEOUT = 120  # seconds: a cold start of the office suite takes a while

_SOFFICE_NAMES = ("soffice", "libreoffice")
_SOFFICE_PATHS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)

# Word's own export (17: wdExportFormatPDF); the paths come from the environment
_WORD_SCRIPT = """
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $document = $word.Documents.Open($env:UNICAP_DOCX, $false, $true)
    $document.ExportAsFixedFormat($env:UNICAP_PDF, 17)
    $document.Close($false)
} finally {
    $word.Quit()
}
"""

Converter = Callable[[Path, Path], None]


class PdfError(UserError):
    """A report that cannot be converted to PDF."""


def to_pdf(docx: bytes) -> bytes:
    """Convert a .docx file's bytes to a PDF file's bytes.

    Raises:
        PdfError: no office suite is installed, or the conversion failed.

    Example:
        ```python
        content = to_pdf(render(path, context))
        ```
    """
    convert = _converter()

    with tempfile.TemporaryDirectory(prefix="unicap-pdf-") as directory:
        source = Path(directory) / "report.docx"
        target = Path(directory) / "report.pdf"

        source.write_bytes(docx)

        try:
            convert(source, target)
        except (OSError, subprocess.SubprocessError) as error:
            msg = _("The PDF cannot be made: %(error)s") % {"error": error}
            raise PdfError(msg) from error

        if not target.exists():
            msg = _("The PDF cannot be made: the converter wrote no file.")
            raise PdfError(msg)

        return target.read_bytes()


def soffice_path() -> str | None:
    """LibreOffice's `soffice`: the `SOFFICE_PATH` setting, the PATH, or its usual folders."""
    if configured := getattr(settings, "SOFFICE_PATH", ""):
        return configured

    for name in _SOFFICE_NAMES:
        if found := shutil.which(name):
            return found

    return next((path for path in _SOFFICE_PATHS if Path(path).exists()), None)


def _converter() -> Converter:
    if soffice := soffice_path():
        return lambda source, target: _with_soffice(soffice, source, target)

    if os.name == "nt" and (powershell := shutil.which("powershell")):
        return lambda source, target: _with_word(powershell, source, target)

    msg = _("A PDF needs LibreOffice on the server (set SOFFICE_PATH), or Word on Windows.")
    raise PdfError(msg)


def _with_soffice(soffice: str, source: Path, target: Path) -> None:
    """`soffice --convert-to pdf`, with a profile of its own so conversions never collide."""
    profile = (target.parent / "profile").as_uri()

    command = [
        soffice,
        f"-env:UserInstallation={profile}",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(target.parent),
        str(source),
    ]

    subprocess.run(command, check=True, capture_output=True, timeout=TIMEOUT)  # noqa: S603


def _with_word(powershell: str, source: Path, target: Path) -> None:
    command = [powershell, "-NoProfile", "-NonInteractive", "-Command", _WORD_SCRIPT]
    environment = {**os.environ, "UNICAP_DOCX": str(source), "UNICAP_PDF": str(target)}

    subprocess.run(  # noqa: S603
        command, check=True, capture_output=True, timeout=TIMEOUT, env=environment
    )
