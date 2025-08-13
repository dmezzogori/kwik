"""
Test configuration and fixtures for the kwik project.

This module provides pytest fixtures for:
- PostgreSQL test container setup
- Database engine and session management
- Test settings configuration
- Admin user creation for testing
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from testcontainers.postgres import PostgresContainer

from kwik.crud import Context
from kwik.database import create_engine, create_session
from kwik.models import Base
from kwik.settings import BaseKwikSettings
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

    from kwik.models import User


@pytest.fixture(scope="session")
def postgres() -> Generator[PostgresContainer, None, None]:
    """Set up a PostgreSQL container for testing."""
    with PostgresContainer(
        "postgres:15-alpine",
        port=5432,
        username="postgres",
        password="root",
        dbname="kwik_test",
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def settings(postgres: PostgresContainer) -> BaseKwikSettings:
    """
    Create and return BaseKwikSettings configured for the test PostgreSQL container.

    Parameters
    ----------
    postgres : PostgresContainer
        The test PostgreSQL container instance.

    Returns
    -------
    BaseKwikSettings
        Settings object configured for the test database.

    """
    return BaseKwikSettings(
        POSTGRES_SERVER=postgres.get_container_host_ip(),
        POSTGRES_PORT=str(postgres.get_exposed_port(5432)),
        POSTGRES_DB="kwik_test",
        POSTGRES_USER="postgres",
        POSTGRES_PASSWORD="root",
    )


@pytest.fixture(scope="session", autouse=True)
def engine(settings: BaseKwikSettings) -> Generator[Engine, None, None]:
    """Set up the database engine for testing."""
    engine = create_engine(settings)

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session")
def admin_user(settings: BaseKwikSettings, engine: Engine) -> User:
    """Create shared admin user using settings credentials for all test suites."""
    session = create_session(engine=engine)
    try:
        context = Context(session=session, user=None)
        user = create_test_user(
            name="admin",
            surname="admin",
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_active=True,
            context=context,
        )
        # Commit the user to make it available to all test suites
        session.commit()
        # Access all attributes to ensure they're loaded before closing session
        _ = (user.id, user.name, user.surname, user.email, user.is_active, user.hashed_password)
        return user
    finally:
        session.close()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Create a database session with transaction rollback for test isolation."""
    session = create_session(engine=engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
