"""API-specific pytest fixtures for FastAPI testing with authentication support."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import Request, status
from fastapi.testclient import TestClient

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.database import session_scope
from kwik.dependencies.session import _get_session

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session as _Session

    from kwik.models import User
    from kwik.settings import BaseKwikSettings


def _non_committing_get_session(request: Request) -> Generator[_Session, None, None]:
    session: _Session = request.app.state.SessionLocal()
    with session_scope(session=session, commit=False) as session:
        yield session


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Set up the Kwik application for testing."""
    kwik = Kwik(settings, api_router)
    kwik.app.dependency_overrides[_get_session] = _non_committing_get_session
    return kwik


@pytest.fixture
def client(kwik_app: Kwik) -> Generator[TestClient, None, None]:
    """Set up an HTTP client for testing."""
    fastapi_app = kwik_app._app
    with TestClient(app=fastapi_app) as client:
        yield client


@pytest.fixture
def admin_token(admin_user: User, client: TestClient, settings: BaseKwikSettings) -> str:
    """Authenticate admin user and return JWT token."""
    response = client.post(
        "/api/v1/login/access-token",
        data={
            "username": admin_user.email,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    assert response.status_code == status.HTTP_200_OK, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def admin_client(client: TestClient, admin_token: str) -> TestClient:
    """TestClient pre-configured with admin authentication headers."""
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {admin_token}",
    }
    return client
