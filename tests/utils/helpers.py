"""Helper functions for testing database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.crud import NoUserCtx, UserCtx, crud_permissions, crud_roles, crud_users
from kwik.schemas import PermissionDefinition, RoleDefinition, UserRegistration

if TYPE_CHECKING:
    from kwik.models import Permission, Role, User


def create_test_user(  # noqa: PLR0913
    *,
    name: str = "testuser",
    surname: str = "testsurname",
    email: str = "test@example.com",
    password: str = "testpassword123",
    is_active: bool = True,
    context: NoUserCtx,
) -> User:
    """Create a test user with the specified parameters."""
    return crud_users.create(
        obj_in=UserRegistration(
            name=name,
            surname=surname,
            email=email,
            password=password,
            is_active=is_active,
        ),
        context=context,
    )


def create_test_role(*, name: str = "test_role", is_active: bool = True, context: UserCtx) -> Role:
    """Create a test role with the specified parameters."""
    obj_in = RoleDefinition(name=name, is_active=is_active)
    return crud_roles.create(obj_in=obj_in, context=context)


def create_test_permission(*, name: str = "test_permission", context: UserCtx) -> Permission:
    """Create a test permission with the specified parameters."""
    obj_in = PermissionDefinition(name=name)
    return crud_permissions.create(obj_in=obj_in, context=context)
