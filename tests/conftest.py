"""Pytest configuration and fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

import kwik
from kwik import configure_kwik
from kwik.api.api import api_router
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

    from kwik.models import User


@pytest.fixture(scope="session")
def setup_test_database() -> Generator[None, None, None]:
    """Ensure test settings are properly configured. Create all database tables for testing."""
    with PostgresContainer("postgres:15-alpine", username="postgres", password="root", dbname="kwik_test") as postgres:
        # Set additional environment variables to match docker-compose config
        postgres.with_env("POSTGRES_INITDB_ARGS", "--encoding=UTF-8")

        # Get dynamic connection details from the container
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)  # PostgreSQL default port inside container

        configure_kwik(
            config_dict={
                "POSTGRES_SERVER": host,
                "POSTGRES_PORT": str(port),
                "POSTGRES_DB": "kwik_test",
                "POSTGRES_USER": "postgres",
                "POSTGRES_PASSWORD": "root",
            },
        )
        # Reset caches after configuration to ensure fresh instances with new settings
        reset_engines()
        reset_session_locals()

        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def db_session(setup_test_database: None) -> Generator[Session, None, None]:  # noqa: ARG001
    """Create a test database session with transaction rollback."""
    session_factory = get_session_local()
    session = session_factory()
    try:
        db_conn_ctx_var.set(session)
        yield session
    finally:
        session.rollback()
        session.close()


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
