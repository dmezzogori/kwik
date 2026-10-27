"""API-specific pytest fixtures for FastAPI testing with authentication support."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm.session import Session

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.auth import InMemoryAuthSessionStore
from kwik.dependencies.session import _get_session
from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine

    from kwik.settings import BaseKwikSettings


@pytest.fixture(scope="session")
def auth_store() -> InMemoryAuthSessionStore:
    """Return the in-memory auth session store the ``kwik_app`` fixture is configured with."""
    return InMemoryAuthSessionStore()


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings, auth_store: InMemoryAuthSessionStore) -> Kwik:
    """Create a Kwik application instance with auth sessions enabled."""
    return Kwik(settings=settings, api_router=api_router, auth_session_store=auth_store)


@pytest.fixture(scope="session")
def legacy_kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Create a Kwik application instance without an auth session store (kwik 1.13 behaviour)."""
    return Kwik(settings=settings, api_router=api_router)


def _rolled_back_client(app: Kwik, engine: Engine) -> Generator[TestClient, None, None]:
    """
    Yield an HTTP client for ``app`` whose requests share one rolled-back transaction.

    The API session joins an outer transaction in ``create_savepoint`` mode, so the
    commit kwik issues before every response only releases a SAVEPOINT and the
    test's writes are discarded at teardown.
    """
    connection = engine.connect()
    transaction = connection.begin()
    api_session = Session(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")

    def _get_session_override() -> Generator[Session, None, None]:
        yield api_session

    app.app.dependency_overrides[_get_session] = _get_session_override
    try:
        with TestClient(app=app.app) as client:
            yield client
    finally:
        app.app.dependency_overrides.pop(_get_session, None)
        api_session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(kwik_app: Kwik, engine: Engine) -> Generator[TestClient, None, None]:
    """Set up an HTTP client for the session-aware application."""
    yield from _rolled_back_client(kwik_app, engine)


@pytest.fixture
def legacy_client(legacy_kwik_app: Kwik, engine: Engine) -> Generator[TestClient, None, None]:
    """Set up an HTTP client for the application without an auth session store."""
    yield from _rolled_back_client(legacy_kwik_app, engine)


@pytest.fixture
def identity_aware_client(client: TestClient, settings: BaseKwikSettings) -> IdentityAwareTestClient:
    """TestClient with identity-aware authentication context switching."""
    return IdentityAwareTestClient(client, settings)
