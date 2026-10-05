"""`manage.py report_templates`: (re)write the built-in Word templates of every report."""

from typing import Any

from django.core.management.base import BaseCommand

from ...reports import build_defaults


class Command(BaseCommand):
    """`manage.py report_templates`."""

    help = "Write the built-in Word templates (reports/defaults/<report>.<language>.docx)."

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        """Write every report's template in every language."""
        for path in build_defaults():
            self.stdout.write(f"wrote {path.name}")
