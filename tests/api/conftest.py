"""API-specific pytest fixtures for FastAPI testing with authentication support."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm.session import Session

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.dependencies.session import _get_session
from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine

    from kwik.settings import BaseKwikSettings


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Create and return a Kwik application instance for testing."""
    return Kwik(settings=settings, api_router=api_router)


@pytest.fixture
def client(kwik_app: Kwik, engine: Engine) -> Generator[TestClient, None, None]:
    """
    Set up an HTTP client whose requests share one rolled-back transaction.

    The API session joins an outer transaction in ``create_savepoint`` mode, so the
    commit kwik issues before every response only releases a SAVEPOINT and the
    test's writes are discarded at teardown.
    """
    connection = engine.connect()
    transaction = connection.begin()
    api_session = Session(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")

    def _get_session_override() -> Generator[Session, None, None]:
        yield api_session

    kwik_app.app.dependency_overrides[_get_session] = _get_session_override
    try:
        with TestClient(app=kwik_app.app) as client:
            yield client
    finally:
        kwik_app.app.dependency_overrides.pop(_get_session, None)
        api_session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def identity_aware_client(client: TestClient, settings: BaseKwikSettings) -> IdentityAwareTestClient:
    """TestClient with identity-aware authentication context switching."""
    return IdentityAwareTestClient(client, settings)
