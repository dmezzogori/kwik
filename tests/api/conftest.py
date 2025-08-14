"""API-specific pytest fixtures for FastAPI testing with authentication support."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm.session import Session

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.database import create_session
from kwik.dependencies.session import _get_session

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from kwik.models import User
    from kwik.settings import BaseKwikSettings


@pytest.fixture
def client(settings: BaseKwikSettings, engine: Engine) -> Generator[TestClient, None, None]:
    """
    Set up an HTTP client for testing.

    This client will use the FastAPI application instance and the API session
    for making requests during testing.
    The API database session will be rolled back after each test to ensure a clean state.
    """
    api_session = create_session(engine=engine)

    def _get_session_override() -> Generator[Session, None, None]:
        yield api_session

    kwik = Kwik(settings=settings, api_router=api_router)
    kwik.app.dependency_overrides[_get_session] = _get_session_override

    with TestClient(app=kwik.app) as client:
        yield client

    api_session.rollback()
    api_session.close()


@pytest.fixture
def admin_client(
    client: TestClient,
    admin_user: User,
    settings: BaseKwikSettings,
) -> TestClient:
    """TestClient pre-configured with admin authentication headers."""
    response = client.post(
        "/api/v1/login/access-token",
        data={
            "username": admin_user.email,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    assert response.status_code == status.HTTP_200_OK, f"Login failed: {response.text}"
    admin_token = response.json()["access_token"]

    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {admin_token}",
    }
    return client
