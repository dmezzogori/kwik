"""Testing-specific pytest fixtures for testing the testing infrastructure itself."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kwik.crud import Context
from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.crud import UserCtx
    from kwik.models import User
    from kwik.settings import BaseKwikSettings


@pytest.fixture
def mock_auth_app() -> FastAPI:
    """
    Create a mock FastAPI app for testing authentication scenarios.

    This app provides controllable endpoints for testing error conditions
    in the IdentityAwareTestClient.
    """
    app = FastAPI()

    # Mock successful authentication endpoint
    @app.post("/api/v1/login/access-token")
    def mock_login() -> dict[str, str]:
        return {"access_token": "test_token_123", "token_type": "bearer"}

    return app


@pytest.fixture
def mock_failing_auth_app() -> FastAPI:
    """Create a mock FastAPI app that returns authentication failures."""
    app = FastAPI()

    @app.post("/api/v1/login/access-token")
    def failing_login() -> tuple[dict[str, str], HTTPStatus]:
        return {"error": "Invalid credentials"}, HTTPStatus.UNAUTHORIZED

    return app


@pytest.fixture
def mock_malformed_auth_app() -> FastAPI:
    """Create a mock FastAPI app that returns malformed JSON."""
    app = FastAPI()

    @app.post("/api/v1/login/access-token")
    def malformed_login() -> dict[str, str]:
        return {"invalid": "response"}

    return app


@pytest.fixture
def mock_client(mock_auth_app: FastAPI) -> TestClient:
    """TestClient for the mock authentication app."""
    return TestClient(mock_auth_app)


@pytest.fixture
def failing_mock_client(mock_failing_auth_app: FastAPI) -> TestClient:
    """TestClient for the failing authentication app."""
    return TestClient(mock_failing_auth_app)


@pytest.fixture
def malformed_mock_client(mock_malformed_auth_app: FastAPI) -> TestClient:
    """TestClient for the malformed authentication app."""
    return TestClient(mock_malformed_auth_app)


@pytest.fixture
def test_user_for_testing(session: Session, admin_context: UserCtx) -> User:  # noqa: ARG001
    """
    Create a test user specifically for testing the testing infrastructure.

    This user has a unique email pattern that doesn't match the standard
    patterns in IdentityAwareTestClient, allowing us to test the fallback behavior.
    """
    from kwik.crud import crud_users  # noqa: PLC0415
    from kwik.schemas import UserRegistration  # noqa: PLC0415

    no_user_context = Context(session=session, user=None)

    return crud_users.create(
        obj_in=UserRegistration(
            name="testuser",
            surname="testing",
            email="unknown.pattern@testing.com",  # Doesn't match known patterns
            password="testpassword123",
            is_active=True,
        ),
        context=no_user_context,
    )


@pytest.fixture
def identity_client_with_settings(mock_client: TestClient, settings: BaseKwikSettings) -> IdentityAwareTestClient:
    """IdentityAwareTestClient with settings for testing admin user detection."""
    return IdentityAwareTestClient(mock_client, settings)


@pytest.fixture
def identity_client_no_settings(mock_client: TestClient) -> IdentityAwareTestClient:
    """IdentityAwareTestClient without settings for testing default behavior."""
    return IdentityAwareTestClient(mock_client, None)
