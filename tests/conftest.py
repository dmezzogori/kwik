"""Pytest configuration and fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

import kwik
from kwik import configure_kwik
from kwik.api.api import api_router
from kwik.core.settings import BaseKwikSettings, reset_settings
from kwik.database.base import Base
from kwik.database.context_vars import db_conn_ctx_var
from kwik.database.engine import get_engine, reset_engines
from kwik.database.override_current_user import override_current_user
from kwik.database.session_local import get_session_local, reset_session_locals
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI
    from sqlalchemy.orm import Session

    from kwik.models.user import User


class TestSettings(BaseKwikSettings):
    """Test-specific settings configuration."""

    TEST_ENV: bool = True


# Configure Kwik with test settings at module level
configure_kwik(
    settings_class=TestSettings,
    config_dict={
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5433",
        "POSTGRES_DB": "kwik_test",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "root",
    },
)


@pytest.fixture(scope="session")
def test_settings_configured() -> None:
    """Ensure test settings are properly configured."""
    # Reset and reconfigure to ensure clean state
    reset_settings()
    reset_engines()  # Clear cached engines so they use new settings
    reset_session_locals()  # Clear cached session factories
    configure_kwik(
        settings_class=TestSettings,
        config_dict={
            "POSTGRES_SERVER": "localhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "kwik_test",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "root",
        },
    )
    # Reset caches again after configuration to ensure fresh instances with new settings
    reset_engines()
    reset_session_locals()


@pytest.fixture(scope="session")
def setup_test_database(test_settings_configured: None) -> Generator[None, None, None]:  # noqa: ARG001
    """Create all database tables for testing."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_test_database: None) -> Generator[Session, None, None]:  # noqa: ARG001
    """Create a test database session with transaction rollback."""
    session_factory = get_session_local()
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user in the current database session."""
    return create_test_user(
        db_session,
        name="testuser",
        surname="testsurname",
        email="test@example.com",
        password="testpassword123",  # noqa: S106
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
    db_conn_ctx_var.set(db_session)

    with TestClient(app) as c:
        yield c

    # Clean up the context variable
    db_conn_ctx_var.set(None)


@pytest.fixture
def client_no_auth(app: FastAPI, db_session: Session) -> Generator[TestClient, None, None]:
    """Create test client with database session but without user context (for unauthenticated tests)."""
    # Set the database session in the context variable
    db_conn_ctx_var.set(db_session)

    with TestClient(app) as c:
        yield c

    # Clean up the context variable
    db_conn_ctx_var.set(None)


@pytest.fixture
def clean_db(db_session: Session) -> Generator[None, None, None]:
    """Clean database tables between tests."""
    # Delete all data from tables (in reverse order to handle foreign keys)
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
    yield
    # Rollback any changes made during the test
    db_session.rollback()


@pytest.fixture
def clean_settings() -> Generator[None, None, None]:
    """Reset settings system between tests to ensure isolation."""
    # Reset settings before test runs
    reset_settings()
    yield
    # Reset settings after test completes
    reset_settings()
