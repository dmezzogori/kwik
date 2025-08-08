"""Root pytest configuration and shared fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from testcontainers.postgres import PostgresContainer

from kwik import configure_kwik
from kwik.database.engine import get_engine, reset_engine
from kwik.database.session_local import reset_session_local
from kwik.models.base import Base

if TYPE_CHECKING:
    from collections.abc import Generator


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
        reset_engine()
        reset_session_local()

        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
