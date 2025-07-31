"""Pytest configuration and fixtures."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment before importing kwik
os.environ["TEST_ENV"] = "True"
os.environ["POSTGRES_SERVER"] = "localhost"
os.environ["POSTGRES_PORT"] = "5433"
os.environ["POSTGRES_DB"] = "kwik_test"
os.environ["POSTGRES_USER"] = "postgres"
os.environ["POSTGRES_PASSWORD"] = "root"

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

import kwik
from kwik.api.api import api_router
from kwik.core.settings import reset_settings
from kwik.database.base import Base
from kwik.database.override_current_user import override_current_user
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI
    from sqlalchemy.engine import Engine

    from kwik.models.user import User


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    """Create test database engine."""
    test_db_url = "postgresql://postgres:root@localhost:5433/kwik_test"
    return create_engine(
        test_db_url,
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL debugging
    )


@pytest.fixture(scope="session")
def test_session_factory(test_engine: Engine) -> sessionmaker:
    """Create test session factory."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_engine: Engine) -> Generator[None, None, None]:
    """Create all database tables for testing."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_session_factory: sessionmaker) -> Generator[Session, None, None]:
    """Create a test database session with transaction rollback."""
    session = test_session_factory()
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
        password="testpassword123",
    )


@pytest.fixture
def user_context(test_user) -> Generator[None, None, None]:  # noqa: ANN001
    """Set up user context using framework's override_current_user."""
    with override_current_user(test_user):
        yield


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application instance for testing."""
    k = kwik.Kwik(api_router)
    return k._app


@pytest.fixture
def client(app: FastAPI, db_session: Session, user_context: None) -> Generator[TestClient, None, None]:
    """Create test client with database session and user context."""
    from kwik.database.context_vars import db_conn_ctx_var

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
