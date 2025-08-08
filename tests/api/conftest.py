"""API-specific pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

import kwik
from kwik.api.api import api_router
from kwik.database.context_vars import db_conn_ctx_var
from kwik.database.override_current_user import override_current_user
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI
    from sqlalchemy.orm import Session

    from kwik.models import User


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user in the current database session."""
    return create_test_user(
        name="testuser",
        surname="testsurname",
        email="test@example.com",
        password="testpassword123",
    )


@pytest.fixture
def user_context(test_user: User) -> Generator[None, None, None]:
    """Set up user context using framework's override_current_user."""
    with override_current_user(test_user):
        yield


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create FastAPI application instance for testing."""
    k = kwik.Kwik(api_router)
    return k._app


@pytest.fixture
def client(app: FastAPI, db_session: Session, user_context: None) -> Generator[TestClient, None, None]:  # noqa: ARG001
    """Create test client with database session and user context."""
    # Set the database session in the context variable

    with TestClient(app) as c:
        yield c

    # Clean up the context variable
    db_conn_ctx_var.set(None)


@pytest.fixture
def client_no_auth(app: FastAPI, db_session: Session) -> Generator[TestClient, None, None]:
    """Create test client with database session but without user context (for unauthenticated tests)."""
    # Set the database session in the context variable

    with TestClient(app) as c:
        yield c

    # Clean up the context variable
    db_conn_ctx_var.set(None)
