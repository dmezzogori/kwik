"""Helper functions for testing database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.testing import Scenario

if TYPE_CHECKING:
    from kwik.crud import NoUserCtx, UserCtx
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
    scenario = Scenario().with_user(
        name=name,
        surname=surname,
        email=email,
        password=password,
        is_active=is_active,
    )
    result = scenario.build(session=context.session)
    return result.users[name]


def create_test_role(*, name: str = "test_role", is_active: bool = True, context: UserCtx) -> Role:
    """Create a test role with the specified parameters."""
    scenario = Scenario().with_role(name=name, is_active=is_active)
    result = scenario.build(session=context.session, admin_user=context.user)
    return result.roles[name]


def create_test_permission(*, name: str = "test_permission", context: UserCtx) -> Permission:
    """Create a test permission with the specified parameters."""
    scenario = Scenario()
    scenario._custom_permissions.add(name)
    result = scenario.build(session=context.session, admin_user=context.user)
    return result.permissions[name]
