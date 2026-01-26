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

from kwik.core.enum import Permissions
from kwik.crud import Context, NoUserCtx, UserCtx, crud_permissions, crud_roles, crud_users
from kwik.database import create_engine, create_session, session_scope
from kwik.models import Base
from kwik.schemas import PermissionDefinition, RoleDefinition, UserRegistration
from kwik.settings import BaseKwikSettings

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
    engine = create_engine(settings)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def admin_user(settings: BaseKwikSettings, engine: Engine) -> User:
    """Create a shared admin user and ensure an admin role with permissions exists."""
    _session = create_session(engine=engine)
    with session_scope(session=_session, commit=True) as scoped_session:
        no_user_context = Context(session=scoped_session, user=None)

        # Check if admin user already exists (idempotent for multi-conftest scenarios)
        existing_user = crud_users.get_by_email(
            email=settings.FIRST_SUPERUSER,
            context=no_user_context,
        )
        if existing_user is not None:
            scoped_session.refresh(existing_user)
            return existing_user

        # Create admin user (email/password from settings)
        admin_user = crud_users.create(
            obj_in=UserRegistration(
                name="admin",
                surname="admin",
                email=settings.FIRST_SUPERUSER,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                is_active=True,
            ),
            context=no_user_context,
        )

        admin_context = Context(session=scoped_session, user=admin_user)

        # Create admin role
        admin_role = crud_roles.create(
            obj_in=RoleDefinition(name="admin", is_active=True),
            context=admin_context,
        )

        # Assign all permissions to admin role
        for permission_name in Permissions:
            permission = crud_permissions.create(
                obj_in=PermissionDefinition(name=permission_name.value),
                context=admin_context,
            )
            crud_roles.assign_permission(role=admin_role, permission=permission, context=admin_context)

        # Assign admin user to the role
        crud_roles.assign_user(role=admin_role, user=admin_user, context=admin_context)

        scoped_session.refresh(admin_user)
        return admin_user


@pytest.fixture(scope="session", autouse=True)
def regular_user(engine: Engine) -> User:
    """Create a shared regular user for impersonation and auth tests."""
    _session = create_session(engine=engine)
    with session_scope(session=_session, commit=True) as scoped_session:
        regular_user = crud_users.create_if_not_exist(
            obj_in=UserRegistration(
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
def admin_context(session: Session, admin_user: User) -> UserCtx:
    """Context with admin user for privileged CRUD operations."""
    return Context(session=session, user=admin_user)
