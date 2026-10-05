"""Browser tests (`uv run pytest -m slow`): a real Chromium on the live test server.

They need the built frontend (`npm run build`) and Playwright's Chromium
(`uv run playwright install chromium`); without the build they are skipped.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.test import Client
from django_vite.core.asset_loader import DjangoViteAssetLoader
from playwright.sync_api import Browser, Page, sync_playwright
from pytest_django.fixtures import Settings
from pytest_django.live_server_helper import LiveServer

from unicap.app.models import Chapter, User

# Playwright's sync API runs an event loop in this thread; the ORM calls of fixtures and
# assertions are still plain blocking calls
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

MANIFEST = Path(django_settings.BASE_DIR) / "static" / "dist" / "manifest.json"


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        yield chromium
        chromium.close()


@pytest.fixture
def built_assets(settings: Settings) -> Iterator[None]:
    """Serve the built JS and CSS (the fast tests point at the Vite dev server instead)."""
    if not MANIFEST.exists():
        pytest.skip("the frontend is not built: run `npm run build`")

    settings.DJANGO_VITE = {
        "default": {"dev_mode": False, "static_url_prefix": "dist", "manifest_path": MANIFEST},
    }
    DjangoViteAssetLoader._instance = None  # noqa: SLF001 - it read the settings once
    yield
    DjangoViteAssetLoader._instance = None  # noqa: SLF001


@pytest.fixture
def page(
    browser: Browser,
    live_server: LiveServer,
    built_assets: None,
    chapter: Chapter,
    admin_user: User,
) -> Iterator[Page]:
    """A page of an admin already logged in, on the sample chapter."""
    client = Client()
    client.force_login(admin_user)
    session = client.cookies[django_settings.SESSION_COOKIE_NAME].value

    context = browser.new_context(
        base_url=live_server.url,
        locale="en-US",
        viewport={"width": 1400, "height": 800},
    )
    context.add_cookies(
        [{"name": django_settings.SESSION_COOKIE_NAME, "value": session, "url": live_server.url}]
    )
    context.set_default_timeout(5000)

    tab = context.new_page()
    errors: list[str] = []
    tab.on("pageerror", lambda error: errors.append(str(error)))

    yield tab

    context.close()

    assert not errors, errors  # no test leaves a JavaScript error behind
