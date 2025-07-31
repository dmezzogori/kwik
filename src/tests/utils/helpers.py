"""Helper functions for testing database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.database.base import Base
from kwik.models.user import User, Role, Permission
from kwik.core.security import get_password_hash

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def cleanup_database(db_session: Session) -> None:
    """Clean all data from database tables in correct order to handle foreign keys."""
    # Delete in reverse order to handle foreign key constraints
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()


def create_test_user(
    db_session: Session,
    *,
    name: str = "testuser",
    surname: str = "testsurname",
    email: str = "test@example.com",
    password: str = "testpassword123",
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    """Create a test user with the specified parameters."""
    user = User(
        name=name,
        surname=surname,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=is_active,
        is_superuser=is_superuser,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_test_role(
    db_session: Session,
    *,
    name: str = "test_role",
    is_active: bool = True,
    is_locked: bool = False,
) -> Role:
    """Create a test role with the specified parameters."""
    role = Role(
        name=name,
        is_active=is_active,
        is_locked=is_locked,
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


def create_test_permission(
    db_session: Session,
    *,
    name: str = "test_permission",
) -> Permission:
    """Create a test permission with the specified parameters."""
    permission = Permission(
        name=name,
    )
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission
