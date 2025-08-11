from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer

from kwik.core.settings import BaseKwikSettings
from kwik.models import Base

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture(scope="session")
def postgres() -> Generator[PostgresContainer, None, None]:
    """Set up a PostgreSQL container for testing."""
    with PostgresContainer("postgres:15-alpine", username="postgres", password="root", dbname="kwik_test") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def settings(postgres: PostgresContainer) -> BaseKwikSettings:
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
    engine = create_engine(
        url=settings.SQLALCHEMY_DATABASE_URI,
        pool_pre_ping=True,
        pool_size=settings.POSTGRES_MAX_CONNECTIONS // settings.BACKEND_WORKERS,
        max_overflow=0,
    )

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
