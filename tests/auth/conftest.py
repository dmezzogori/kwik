"""
Fixtures for the kwik.auth tests.

These tests need no database. The kwik pytest plugin starts PostgreSQL through its
``settings`` fixture and three session-scoped autouse fixtures (``engine``, ``admin_user``,
``regular_user``); overriding all four here keeps the container out of this package.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kwik.auth import InMemoryAuthSessionStore
from kwik.settings import BaseKwikSettings


@pytest.fixture(scope="session")
def settings() -> BaseKwikSettings:
    """Build settings from the environment, with no database container behind them."""
    return BaseKwikSettings()


@pytest.fixture(scope="session", autouse=True)
def engine() -> None:
    """Replace the plugin's database engine: these tests touch no database."""


@pytest.fixture(scope="session", autouse=True)
def admin_user() -> None:
    """Replace the plugin's seeded admin user: these tests touch no database."""


@pytest.fixture(scope="session", autouse=True)
def regular_user() -> None:
    """Replace the plugin's seeded regular user: these tests touch no database."""


@pytest.fixture
def store() -> InMemoryAuthSessionStore:
    """Return an empty in-memory session store."""
    return InMemoryAuthSessionStore()


@pytest.fixture
def now() -> datetime:
    """
    Return the current time in whole seconds.

    Every token minted in these tests is decoded and PyJWT checks ``exp`` against the wall
    clock, so the injected clock has to be close to it.
    """
    return datetime.now(UTC).replace(microsecond=0)
