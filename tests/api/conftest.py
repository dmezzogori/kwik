"""API-specific pytest fixtures for FastAPI testing with authentication support."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm.session import Session

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.database import create_session
from kwik.dependencies.session import _get_session
from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from kwik.settings import BaseKwikSettings


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Create and return a Kwik application instance for testing."""
    return Kwik(settings=settings, api_router=api_router)


@pytest.fixture
def client(kwik_app: Kwik, engine: Engine) -> Generator[TestClient, None, None]:
    """
    Set up an HTTP client for testing.

    This client will use the FastAPI application instance and the API session
    for making requests during testing.
    The API database session will be rolled back after each test to ensure a clean state.
    """
    api_session = create_session(engine=engine)

    def _get_session_override() -> Generator[Session, None, None]:
        yield api_session

    kwik_app.app.dependency_overrides[_get_session] = _get_session_override

    with TestClient(app=kwik_app.app) as client:
        yield client

    api_session.rollback()
    api_session.close()


@pytest.fixture
def identity_aware_client(client: TestClient, settings: BaseKwikSettings) -> IdentityAwareTestClient:
    """TestClient with identity-aware authentication context switching."""
    return IdentityAwareTestClient(client, settings)
