"""
Fluent Scenario Builder for enhanced testing infrastructure.

This module provides a fluent API for creating complex test scenarios with users,
roles, permissions, and other entities in a declarative, chainable manner.

Example usage:
    from kwik.testing import Scenario
    from kwik.database import create_session

    session = create_session()
    scenario = (Scenario()
               .with_user(name="john", email="john@test.com", roles=["editor"])
               .with_user(name="jane", admin=True)
               .with_role("editor", permissions=["posts:read", "posts:write"])
               .build(session=session, admin_user=admin_user))

    # Access created entities
    john = scenario.users["john"]
    jane = scenario.users["jane"]
    editor_role = scenario.roles["editor"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.crud import Context, crud_permissions, crud_roles, crud_users
from kwik.schemas import PermissionDefinition, RoleDefinition, UserRegistration

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models import Permission, Role, User


@dataclass
class ScenarioResult:
    """Container for all entities created by a scenario build."""

    users: dict[str, User] = field(default_factory=dict)
    roles: dict[str, Role] = field(default_factory=dict)
    permissions: dict[str, Permission] = field(default_factory=dict)


@dataclass
class UserSpec:
    """Specification for creating a user in a scenario."""

    name: str
    surname: str = "Doe"
    email: str | None = None
    password: str = "testpassword123"  # noqa: S105
    is_active: bool = True
    admin: bool = False
    roles: list[str] = field(default_factory=list)


@dataclass
class RoleSpec:
    """Specification for creating a role in a scenario."""

    name: str
    is_active: bool = True
    permissions: list[str] = field(default_factory=list)


class Scenario:
    """
    Fluent builder for creating complex test scenarios.

    Provides a chainable API for declaratively defining users, roles, and permissions
    with automatic relationship management and sensible defaults.
    """

    def __init__(self) -> None:
        """Initialize a new scenario builder with empty specifications."""
        self._user_specs: list[UserSpec] = []
        self._role_specs: list[RoleSpec] = []
        self._custom_permissions: set[str] = set()

    def with_user(  # noqa: PLR0913
        self,
        *,
        name: str,
        surname: str = "Doe",
        email: str | None = None,
        password: str = "testpassword123",  # noqa: S107
        is_active: bool = True,
        admin: bool = False,
        roles: list[str] | None = None,
    ) -> Scenario:
        """
        Add a user to the scenario.

        Args:
            name: User's first name (used as identifier)
            surname: User's surname (defaults to "Doe")
            email: User's email (auto-generated if None)
            password: User's password (defaults to "testpassword123")
            is_active: Whether user is active (defaults to True)
            admin: Whether user should have admin privileges (defaults to False)
            roles: List of role names to assign to user

        Returns:
            Self for method chaining

        Example:
            scenario.with_user(name="john", email="john@test.com", roles=["editor"])

        """
        if email is None:
            email = f"{name.lower()}@test.com"

        user_roles = roles or []
        if admin:
            user_roles.append("admin")

        self._user_specs.append(
            UserSpec(
                name=name,
                surname=surname,
                email=email,
                password=password,
                is_active=is_active,
                admin=admin,
                roles=user_roles,
            )
        )

        return self

    def with_admin_user(
        self,
        *,
        name: str = "admin",
        surname: str = "Admin",
        email: str | None = None,
        password: str = "adminpassword123",  # noqa: S107
    ) -> Scenario:
        """
        Add an admin user to the scenario (convenience method).

        Args:
            name: Admin user's name (defaults to "admin")
            surname: Admin user's surname (defaults to "Admin")
            email: Admin user's email (auto-generated if None)
            password: Admin user's password (defaults to "adminpassword123")

        Returns:
            Self for method chaining

        Example:
            scenario.with_admin_user(name="superadmin")

        """
        return self.with_user(
            name=name,
            surname=surname,
            email=email,
            password=password,
            admin=True,
        )

    def with_role(
        self,
        name: str,
        *,
        is_active: bool = True,
        permissions: list[str] | None = None,
    ) -> Scenario:
        """
        Add a role to the scenario.

        Args:
            name: Role name
            is_active: Whether role is active (defaults to True)
            permissions: List of permission names to assign to role

        Returns:
            Self for method chaining

        Example:
            scenario.with_role("editor", permissions=["posts:read", "posts:write"])

        """
        role_permissions = permissions or []

        # Track custom permissions for creation
        for perm in role_permissions:
            self._custom_permissions.add(perm)

        self._role_specs.append(
            RoleSpec(
                name=name,
                is_active=is_active,
                permissions=role_permissions,
            )
        )

        return self

    def build(self, *, session: Session, admin_user: User | None = None) -> ScenarioResult:  # noqa: C901, PLR0912
        """
        Build the scenario by creating all specified entities.

        Args:
            session: Database session to use for creation
            admin_user: Admin user to use for creating entities (required for roles/permissions)

        Returns:
            ScenarioResult containing all created entities

        Raises:
            ValueError: If scenario configuration is invalid or admin_user is required but not provided

        """
        result = ScenarioResult()
        admin_context = Context(session=session, user=admin_user) if admin_user else None
        no_user_context = Context(session=session, user=None)

        # Validate that admin operations are only requested when admin_user is provided
        needs_admin = (
            bool(self._custom_permissions)
            or bool(self._role_specs)
            or any(spec.admin or spec.roles for spec in self._user_specs)
        )

        if needs_admin and not admin_user:
            msg = "admin_user is required for scenarios with permissions, roles, admin users, or role assignments"
            raise ValueError(msg)

        # Create custom permissions first
        for permission_name in self._custom_permissions:
            permission = crud_permissions.create(
                obj_in=PermissionDefinition(name=permission_name),
                context=admin_context,
            )
            result.permissions[permission_name] = permission

        # Create roles
        for role_spec in self._role_specs:
            role = crud_roles.create(
                obj_in=RoleDefinition(
                    name=role_spec.name,
                    is_active=role_spec.is_active,
                ),
                context=admin_context,
            )
            result.roles[role_spec.name] = role

            # Assign permissions to role
            for permission_name in role_spec.permissions:
                if permission_name in result.permissions:
                    permission = result.permissions[permission_name]
                else:
                    # Try to find existing permission by enum
                    try:
                        perm_enum = Permissions(permission_name)
                        # Permission should exist from admin user setup
                        permission = crud_permissions.get_by_name(
                            name=perm_enum.value,
                            context=admin_context,
                        )
                        if permission:
                            result.permissions[permission_name] = permission
                        else:
                            self._raise_permission_not_found(permission_name)
                    except ValueError:
                        self._raise_permission_not_found(permission_name)

                crud_roles.assign_permission(
                    role=role,
                    permission=permission,
                    context=admin_context,
                )

        # Create admin role if any admin users are specified
        admin_users = [spec for spec in self._user_specs if spec.admin]
        if admin_users and "admin" not in result.roles:
            admin_role = crud_roles.create(
                obj_in=RoleDefinition(name="admin", is_active=True),
                context=admin_context,
            )
            result.roles["admin"] = admin_role

            # Assign all permissions to admin role
            for perm_enum in Permissions:
                # Get existing permission
                permission = crud_permissions.get_by_name(
                    name=perm_enum.value,
                    context=admin_context,
                )
                if permission:
                    crud_roles.assign_permission(
                        role=admin_role,
                        permission=permission,
                        context=admin_context,
                    )

        # Create users using standard CRUD operations
        for user_spec in self._user_specs:
            user = crud_users.create(
                obj_in=UserRegistration(
                    name=user_spec.name,
                    surname=user_spec.surname,
                    email=user_spec.email,
                    password=user_spec.password,
                    is_active=user_spec.is_active,
                ),
                context=no_user_context,
            )
            result.users[user_spec.name] = user

            # Assign roles to user
            for role_name in user_spec.roles:
                if role_name in result.roles:
                    role = result.roles[role_name]
                    crud_roles.assign_user(
                        role=role,
                        user=user,
                        context=admin_context,
                    )
                else:
                    msg = f"Role '{role_name}' not found for user '{user_spec.name}'"
                    raise ValueError(msg)

        return result

    def _raise_permission_not_found(self, permission_name: str) -> None:
        """Raise ValueError for permission not found."""
        msg = f"Permission '{permission_name}' not found"
        raise ValueError(msg)
