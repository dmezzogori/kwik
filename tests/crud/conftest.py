"""CRUD-specific pytest fixtures."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from kwik import configure_kwik, get_settings
from kwik.crud import Context, NoUserCtx, UserCtx
from kwik.models import Base
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture(scope="session")
def postgres() -> Generator[PostgresContainer, None, None]:
    """Set up a PostgreSQL container for testing."""
    with PostgresContainer("postgres:15-alpine", username="postgres", password="root", dbname="kwik_test") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def engine(postgres: PostgresContainer) -> Generator[Engine, None, None]:
    """Ensure test settings are properly configured. Create all database tables for testing."""
    # TODO: see how to improve the configuration setup boilerplate
    configure_kwik(
        config_dict={
            "POSTGRES_SERVER": postgres.get_container_host_ip(),
            "POSTGRES_PORT": str(postgres.get_exposed_port(5432)),
            "POSTGRES_DB": "kwik_test",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "root",
        },
    )

    settings = get_settings()
    engine = create_engine(
        url=settings.SQLALCHEMY_DATABASE_URI,
        pool_pre_ping=True,
        pool_size=settings.POSTGRES_MAX_CONNECTIONS // settings.BACKEND_WORKERS,
        max_overflow=0,
    )

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def no_user_context(engine: Engine) -> Generator[NoUserCtx, None, None]:
    """Create a test database session with transaction rollback."""
    session_maker = sessionmaker(bind=engine, autoflush=False)
    session = session_maker()
    try:
        yield Context(session=session, user=None)
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def admin_context(engine: Engine) -> Generator[UserCtx, None, None]:
    """Create a test database session with transaction rollback."""
    session_maker = sessionmaker(bind=engine, autoflush=False)
    session = session_maker()
    try:
        admin = create_test_user(
            name="admin",
            surname="surname",
            email="admin@example.com",
            password="password",
            is_active=True,
            context=Context(session=session, user=None),
        )
        yield Context(session=session, user=admin)
    finally:
        session.rollback()
        session.close()
