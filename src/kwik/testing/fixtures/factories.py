"""
Pytest fixtures for enhanced testing with Kwik framework.

This module provides pytest fixtures that act as factories for creating test entities
using the Scenario API. These fixtures are designed to be used both internally by
Kwik's own tests and by external developers using the Kwik framework.

Example usage:
    def test_role_creation(role_factory):
        role = role_factory(name="editor", permissions=["posts:read", "posts:write"])
        assert role.name == "editor"

    def test_multiple_users(user_factory):
        admin = user_factory(name="admin", admin=True)
        user = user_factory(name="john", email="john@test.com")
        assert admin.name == "admin"
        assert user.email == "john@test.com"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.crud import Context
from kwik.testing.scenario import Scenario

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.crud import UserCtx
    from kwik.models import Permission, Role, User


@pytest.fixture
def user_factory(admin_context: UserCtx) -> Callable[..., User]:
    """
    Create a factory fixture for test users using the Scenario API.

    Args:
        admin_context: Admin context fixture (automatically injected)

    Returns:
        Function that creates User objects with specified parameters

    Example:
        def test_user_creation(user_factory):
            user = user_factory(name="john", email="john@example.com")
            admin_user = user_factory(name="admin", admin=True)

    """

    def _create_user(  # noqa: PLR0913
        *,
        name: str = "testuser",
        surname: str = "testsurname",
        email: str | None = None,
        password: str = "testpassword123",  # noqa: S107
        is_active: bool = True,
        admin: bool = False,
        roles: list[str] | None = None,
    ) -> User:
        """Create a test user with the specified parameters."""
        if email is None:
            email = f"{name.lower()}@test.com"

        scenario = Scenario().with_user(
            name=name,
            surname=surname,
            email=email,
            password=password,
            is_active=is_active,
            admin=admin,
            roles=roles or [],
        )

        # For user creation, we need to handle admin users specially
        if admin or roles:
            # Admin users and role assignments need admin_context
            result = scenario.build(session=admin_context.session, admin_user=admin_context.user)
        else:
            # Regular users can be created without admin privileges
            no_user_context = Context(session=admin_context.session, user=None)
            result = scenario.build(session=no_user_context.session, admin_user=admin_context.user)

        return result.users[name]

    return _create_user


@pytest.fixture
def role_factory(admin_context: UserCtx) -> Callable[..., Role]:
    """
    Create a factory fixture for test roles using the Scenario API.

    Args:
        admin_context: Admin context fixture (automatically injected)

    Returns:
        Function that creates Role objects with specified parameters

    Example:
        def test_role_creation(role_factory):
            role = role_factory(name="editor", permissions=["posts:read", "posts:write"])
            admin_role = role_factory(name="admin", is_active=True)

    """

    def _create_role(
        *,
        name: str = "test_role",
        is_active: bool = True,
        permissions: list[str] | None = None,
    ) -> Role:
        """Create a test role with the specified parameters."""
        scenario = Scenario().with_role(
            name=name,
            is_active=is_active,
            permissions=permissions or [],
        )
        result = scenario.build(session=admin_context.session, admin_user=admin_context.user)
        return result.roles[name]

    return _create_role


@pytest.fixture
def permission_factory(admin_context: UserCtx) -> Callable[..., Permission]:
    """
    Create a factory fixture for test permissions using the Scenario API.

    Args:
        admin_context: Admin context fixture (automatically injected)

    Returns:
        Function that creates Permission objects with specified parameters

    Example:
        def test_permission_creation(permission_factory):
            permission = permission_factory(name="posts:read")
            custom_perm = permission_factory(name="custom:action")

    """

    def _create_permission(*, name: str = "test_permission") -> Permission:
        """Create a test permission with the specified name."""
        scenario = Scenario()
        scenario._custom_permissions.add(name)  # noqa: SLF001
        result = scenario.build(session=admin_context.session, admin_user=admin_context.user)
        return result.permissions[name]

    return _create_permission
