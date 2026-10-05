"""`nox -s build`: production assets, requirements files, clean caches."""

import shutil
from pathlib import Path

import nox

ROOT = Path(__file__).parent


@nox.session(venv_backend="none")
def build(session: nox.Session) -> None:
    """Build the frontend, export requirements and remove caches."""
    session.run("npm", "run", "build", external=True)
    session.run(
        "uv",
        "export",
        "--no-hashes",
        "--no-dev",
        "--output-file",
        "requirements.txt",
        external=True,
    )
    session.run(
        "uv",
        "export",
        "--no-hashes",
        "--output-file",
        "dev-requirements.txt",
        external=True,
    )

    for cache in ("htmlcov", ".pytest_cache", ".ruff_cache"):
        shutil.rmtree(ROOT / cache, ignore_errors=True)

    (ROOT / ".coverage").unlink(missing_ok=True)


@nox.session(venv_backend="none")
def check(session: nox.Session) -> None:
    """Lint, format check and tests."""
    session.run("uv", "run", "ruff", "check", ".", external=True)
    session.run("uv", "run", "ruff", "format", "--check", ".", external=True)
    session.run("uv", "run", "pytest", external=True)
