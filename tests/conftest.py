"""
Test configuration and fixtures for the kwik project.

This module provides pytest fixtures for:
- PostgreSQL test container setup
- Database engine and session management
- Test settings configuration
- Admin user creation for testing
- Regular user creation for testing
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from testcontainers.postgres import PostgresContainer

from kwik.core.enum import Permissions
from kwik.crud import Context, crud_permissions, crud_roles
from kwik.database import create_engine, create_session, session_scope
from kwik.models import Base
from kwik.schemas import PermissionDefinition, RoleDefinition
from kwik.settings import BaseKwikSettings
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine

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


@pytest.fixture(scope="session", autouse=True)
def admin_user(settings: BaseKwikSettings, engine: Engine) -> User:
    """Create shared admin user using settings credentials for all test suites."""
    _session = create_session(engine=engine)
    with session_scope(session=_session, commit=True) as scoped_session:
        admin_user = create_test_user(
            name="admin",
            surname="admin",
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_active=True,
            context=Context(session=scoped_session, user=None),
        )
        _ = (
            admin_user.id,
            admin_user.name,
            admin_user.surname,
            admin_user.email,
            admin_user.is_active,
            admin_user.hashed_password,
        )

        admin_context = Context(session=scoped_session, user=admin_user)

        # Create admin role
        admin_role = crud_roles.create(
            obj_in=RoleDefinition(name="admin", is_active=True),
            context=admin_context,
        )

        # Assign all permissions to admin role
        for permission_name in Permissions:
            # Create permission
            permission = crud_permissions.create(
                obj_in=PermissionDefinition(name=permission_name.value),
                context=admin_context,
            )

            # Assign permission to role
            crud_roles.assign_permission(role=admin_role, permission=permission, context=admin_context)

        # Assign admin user to the role
        crud_roles.assign_user(role=admin_role, user=admin_user, context=admin_context)

        scoped_session.refresh(admin_user)

        return admin_user


@pytest.fixture(scope="session", autouse=True)
def regular_user(engine: Engine) -> User:
    """Create a regular user for testing impersonation functionality."""
    _session = create_session(engine=engine)
    with session_scope(session=_session, commit=True) as scoped_session:
        regular_user = create_test_user(
            name="regular",
            surname="user",
            email="regular@example.com",
            password="regularpassword123",
            is_active=True,
            context=Context(session=scoped_session, user=None),
        )
        _ = (regular_user.id, regular_user.name, regular_user.surname, regular_user.email)
        return regular_user
