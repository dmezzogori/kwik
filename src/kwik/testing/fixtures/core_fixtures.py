"""
Core pytest fixtures for Kwik testing.

These fixtures provide a public, reusable baseline to bootstrap a database-backed
testing environment for projects using Kwik. They are intentionally lightweight
and configurable via environment variables, so they work for both this repo and
external users without depending on the test suite internals.

Default behavior:
- `settings`: Builds `BaseKwikSettings` from environment variables (prefix `KWIK_`).
- `engine`: Creates a SQLAlchemy engine using `settings`, creates tables at session start,
  and drops them at the end of the test session.
- `session`: Provides a SQLAlchemy session per test with rollback for isolation.
- `admin_user`/`regular_user`: Convenience users for common testing patterns.
- `admin_context`/`no_user_context`: Ready-to-use CRUD contexts.

Notes:
- External users can override any fixture in their own `conftest.py` to customize behavior
  (e.g., different DB lifecycle, seeded data, etc.).
- No hard dependency on Testcontainers: projects may use environment variables
  to point to a running PostgreSQL instance for tests. See `kwik.settings.BaseKwikSettings`.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from testcontainers.postgres import PostgresContainer

from kwik.crud import Context, NoUserCtx, UserCtx
from kwik.database import create_engine, create_session, session_scope
from kwik.kernel import get_kernel
from kwik.models import Base
from kwik.seeding import create_first_superuser
from kwik.settings import BaseKwikSettings

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

    from kwik.models.user_mixin import UserMixin


@pytest.fixture(scope="session")
def postgres() -> Generator[PostgresContainer, None, None]:
    """Set up a PostgreSQL container for testing."""
    with PostgresContainer(
        "postgres:15-alpine",
        port=5432,
        username="postgres",
        password="root",  # noqa: S106
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
        POSTGRES_PASSWORD="root",  # noqa: S106
    )


@pytest.fixture(scope="session", autouse=True)
def engine(settings: BaseKwikSettings) -> Generator[Engine, None, None]:
    """Create a database engine and manage schema lifecycle for tests."""
    get_kernel()  # ensure the active user model is mapped before create_all
    engine = create_engine(settings)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def admin_user(settings: BaseKwikSettings, engine: Engine) -> UserMixin:
    """Create a shared admin user via the seeding battery (idempotent)."""
    _session = create_session(engine=engine)
    with session_scope(session=_session, commit=True) as scoped_session:
        user = create_first_superuser(session=scoped_session, settings=settings)
        scoped_session.refresh(user)
        return user


@pytest.fixture(scope="session", autouse=True)
def regular_user(engine: Engine) -> UserMixin:
    """Create a shared regular user for impersonation and auth tests."""
    _session = create_session(engine=engine)
    with session_scope(session=_session, commit=True) as scoped_session:
        regular_user = get_kernel().crud_users.create_if_not_exist(
            obj_in=get_kernel().schemas.registration(
                name="regular",
                surname="user",
                email="regular@example.com",
                password="regularpassword123",  # noqa: S106
                is_active=True,
            ),
            context=Context(session=scoped_session, user=None),
            filters={"email": "regular@example.com"},
        )
        _ = (regular_user.id, regular_user.name, regular_user.surname, regular_user.email)
        return regular_user


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    """Yield a DB session with rollback for test isolation."""
    session = create_session(engine=engine)
    with session_scope(session=session, commit=False) as session:
        yield session


@pytest.fixture
def no_user_context(session: Session) -> NoUserCtx:
    """Context without user for non-privileged CRUD operations."""
    return Context(session=session, user=None)


@pytest.fixture
def admin_context(session: Session, admin_user: UserMixin) -> UserCtx:
    """Context with admin user for privileged CRUD operations."""
    return Context(session=session, user=admin_user)
