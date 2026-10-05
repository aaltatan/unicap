"""SQL per page: how many queries each page runs, how many are repeats, and their time.

    uv run python scripts/profile_queries.py            # every page below
    uv run python scripts/profile_queries.py board      # the pages whose name holds "board"

Reads the development database (GET requests only) as a temporary superuser, on the default
chapter. django-silk is left out of these requests (its own queries would be counted); to see
a page's queries one by one, with where each was run from, open the page in the browser and
then /silk/.
"""

import os
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unicap.unicap.settings.development")

import django

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import CaptureQueriesContext, override_settings  # noqa: E402

from unicap.app.models import (  # noqa: E402
    Chapter,
    Contract,
    Employee,
    Faculty,
    Specialization,
    User,
)

HTMX = {"HTTP_HX_REQUEST": "true"}
TABLE = {**HTMX, "HTTP_HX_TARGET": "table"}

USERNAME = "profile-queries"


def pages(chapter: Chapter) -> list[tuple[str, str, dict[str, str]]]:
    """(name, url, headers) of every page worth watching."""
    faculty = Faculty.objects.filter(chapter=chapter, contracts__isnull=False).first()
    employee = Employee.objects.filter(chapter=chapter, contract__isnull=False).first()
    contract = Contract.objects.filter(chapter=chapter, faculty__isnull=False).first()
    specialization = Specialization.objects.filter(chapter=chapter, employees__isnull=False).first()

    return [
        ("dashboard", "/", {}),
        ("board", "/board/", {}),
        ("board preview", f"/board/preview/?employee={employee.pk}", HTMX),
        ("contracts table", "/hr/contracts/", {}),
        ("contracts table (100 rows)", "/hr/contracts/?per_page=100", TABLE),
        ("contracts table (filtered)", "/hr/contracts/?specialization_type=specialized", TABLE),
        ("employees table", "/hr/employees/", {}),
        ("employees table (100 rows)", "/hr/employees/?per_page=100", TABLE),
        ("faculties table", "/edu/faculties/", {}),
        ("specializations table", "/edu/specializations/", {}),
        ("chapters table", "/chapters/", {}),
        ("contract modal", contract.get_absolute_url(), HTMX),
        ("contract form", contract.get_update_url(), HTMX),
        ("employee modal", employee.get_absolute_url(), HTMX),
        ("employee form", employee.get_update_url(), HTMX),
        ("faculty modal", faculty.get_absolute_url(), HTMX),
        ("faculty form", faculty.get_update_url(), HTMX),
        ("specialization modal", specialization.get_absolute_url(), HTMX),
        ("capacity report", "/reports/capacity/", {}),
        ("capacity pivot", "/reports/capacity/pivot/", {}),
        ("calculation audit", "/reports/audit/", {}),
        ("faculty reports", "/reports/faculties/", {}),
        ("staff report", f"/reports/faculties/{faculty.pk}/staff/", {}),
        ("staff pivot", f"/reports/faculties/{faculty.pk}/staff/pivot/", {}),
        ("capacity docx", "/reports/capacity/docx/", {}),
        ("employees export", "/hr/employees/?export=csv", {}),
        ("contracts export", "/hr/contracts/?export=csv", {}),
        ("search", "/search/?q=a", HTMX),
    ]


def measure(
    client: Client, url: str, headers: dict[str, str]
) -> tuple[int, int, int, float, float]:
    """(status, queries, repeated queries, sql ms, total ms) of one request."""
    started = time.perf_counter()

    with CaptureQueriesContext(connection) as captured:
        response = client.get(url, **headers)

        if hasattr(response, "streaming_content"):
            b"".join(response.streaming_content)

    total = (time.perf_counter() - started) * 1000

    queries = captured.captured_queries
    repeats = sum(count - 1 for count in Counter(query["sql"] for query in queries).values())
    sql = sum(float(query["time"]) for query in queries) * 1000

    return response.status_code, len(queries), repeats, sql, total


def main() -> None:
    """Profile the pages as a temporary superuser, removed afterwards."""
    wanted = sys.argv[1] if len(sys.argv) > 1 else ""

    chapter = Chapter.objects.filter(is_default=True).first() or Chapter.objects.first()

    if chapter is None:
        sys.exit("no chapter in the development database: nothing to profile")

    User.objects.filter(username=USERNAME).delete()
    user = User.objects.create_superuser(USERNAME, f"{USERNAME}@example.com", None)

    client = Client(SERVER_NAME="localhost")
    client.force_login(user)

    without_silk = [name for name in settings.MIDDLEWARE if "silk" not in name]

    print(f"chapter: {chapter.pk}, {chapter.employees.count()} employees")
    print(f"{'page':<30}{'status':>7}{'queries':>9}{'repeats':>9}{'sql ms':>9}{'total ms':>10}")

    try:
        with override_settings(MIDDLEWARE=without_silk):
            profile(client, pages(chapter), wanted)
    finally:
        user.delete()


def profile(client: Client, found: list[tuple[str, str, dict[str, str]]], wanted: str) -> None:
    """Print one line per page whose name holds `wanted`."""
    for name, url, headers in found:
        if wanted not in name:
            continue

        measure(client, url, headers)  # warm up: templates, settings caches
        status, queries, repeats, sql, total = measure(client, url, headers)

        print(f"{name:<30}{status:>7}{queries:>9}{repeats:>9}{sql:>9.0f}{total:>10.0f}")


if __name__ == "__main__":
    main()
