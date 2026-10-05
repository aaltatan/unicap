"""Shared fixtures: the sample chapter, and clients for users with and without permissions."""

from collections.abc import Iterator

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.cache import caches
from django.test import Client
from django.utils import translation

from unicap.app.management.commands.seed import sample_chapter
from unicap.app.models import Chapter, User


@pytest.fixture(autouse=True)
def default_language() -> Iterator[None]:
    """Each test starts in the default language: a request in Arabic leaves it active."""
    yield
    translation.activate(settings.LANGUAGE_CODE)


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    """django-solo caches the settings singletons: each test reads its own database."""
    caches[settings.SOLO_CACHE].clear()
    yield
    caches[settings.SOLO_CACHE].clear()


@pytest.fixture
def chapter(db: None) -> Chapter:
    """The sample chapter (pucc's sample university), saved through `create_from_domain`."""
    return Chapter.objects.create_from_domain(sample_chapter("2026 / Fall"))


@pytest.fixture
def admin_user(db: None) -> User:
    return User.objects.create_superuser("admin", "admin@example.com", "password")


@pytest.fixture
def viewer(db: None) -> User:
    """A user who may only look: every `view_*` permission, nothing else."""
    user = User.objects.create_user("viewer", password="password")  # noqa: S106
    user.user_permissions.set(Permission.objects.filter(codename__startswith="view_"))
    return user


@pytest.fixture
def admin_client(admin_user: User) -> Client:
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def viewer_client(viewer: User) -> Client:
    client = Client()
    client.force_login(viewer)
    return client


HTMX = {"HTTP_HX_REQUEST": "true"}


def htmx(target: str | None = None) -> dict[str, str]:
    """Headers of an HTMX request (targeting `target`)."""
    headers = dict(HTMX)

    if target:
        headers["HTTP_HX_TARGET"] = target

    return headers
