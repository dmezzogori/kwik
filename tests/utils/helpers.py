"""Helper functions for testing database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.security import get_password_hash
from kwik.database.base import Base
from kwik.database.context_vars import current_user_ctx_var
from kwik.models.user import Permission, Role, User

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def cleanup_database(db_session: Session) -> None:
    """Clean all data from database tables in correct order to handle foreign keys."""
    # Delete in reverse order to handle foreign key constraints
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()


def create_test_user(  # noqa: PLR0913
    db_session: Session,
    *,
    name: str = "testuser",
    surname: str = "testsurname",
    email: str = "test@example.com",
    password: str = "testpassword123",
    is_active: bool = True,
) -> User:
    """Create a test user with the specified parameters."""
    user = User(
        name=name,
        surname=surname,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=is_active,
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
    creator_user_id: int | None = None,
) -> Role:
    """Create a test role with the specified parameters."""
    # Use provided creator_user_id or fallback to current user context
    if creator_user_id is None:
        current_user = current_user_ctx_var.get()
        if current_user is not None:
            creator_user_id = current_user.id

    role_kwargs = {
        "name": name,
        "is_active": is_active,
    }

    # Only add creator_user_id if we have one (avoids NULL constraint error)
    if creator_user_id is not None:
        role_kwargs["creator_user_id"] = creator_user_id

    role = Role(**role_kwargs)
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


def create_test_permission(
    db_session: Session,
    *,
    name: str = "test_permission",
    creator_user_id: int | None = None,
) -> Permission:
    """Create a test permission with the specified parameters."""
    # Use provided creator_user_id or fallback to current user context
    if creator_user_id is None:
        current_user = current_user_ctx_var.get()
        if current_user is not None:
            creator_user_id = current_user.id

    permission_kwargs = {
        "name": name,
    }

    # Only add creator_user_id if we have one (avoids NULL constraint error)
    if creator_user_id is not None:
        permission_kwargs["creator_user_id"] = creator_user_id

    permission = Permission(**permission_kwargs)
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission
