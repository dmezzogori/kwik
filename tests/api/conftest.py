"""API-specific pytest fixtures for FastAPI testing with authentication support."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.crud import Context
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session

    from kwik.core.settings import BaseKwikSettings
    from kwik.models import User


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Set up the Kwik application for testing."""
    return Kwik(settings, api_router)


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
def authenticated_client(client: TestClient, admin_token: str) -> TestClient:
    """TestClient pre-configured with admin authentication headers."""
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {admin_token}",
    }
    return client


@pytest.fixture
def regular_user(db_session: Session) -> User:
    """Create a regular (non-admin) user in the database for API testing."""
    context = Context(session=db_session, user=None)
    user = create_test_user(
        name="testuser",
        surname="testuser",
        email="user@example.com",
        password="password",
        is_active=True,
        context=context,
    )
    # Commit the user to make it available to API endpoints
    db_session.commit()
    return user
