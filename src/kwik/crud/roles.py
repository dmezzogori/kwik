"""CRUD operations for roles database entities."""

from __future__ import annotations

from sqlalchemy import or_, select

from kwik.models import Permission, Role, RolePermission, User, UserRole
from kwik.schemas import RoleDefinition, RoleUpdate

from .autocrud import AutoCRUD
from .context import UserCtx


class CRUDRole(AutoCRUD[UserCtx, Role, RoleDefinition, RoleUpdate]):
    """CRUD operations for roles with user and permission management."""

    def get_by_name(self, *, name: str) -> Role | None:
        """Get role by name."""
        stmt = select(Role).where(Role.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_users_with(self, *, role: Role) -> list[User]:
        """Get all users associated with a specific role."""
        return role.users

    def get_users_without(self, *, role_id: int) -> list[User]:
        """Get all users not involved in the given role, including users with no role."""
        stmt = (
            select(User)
            .outerjoin(UserRole, User.id == UserRole.user_id)
            .filter(or_(UserRole.role_id.is_(None), UserRole.role_id != role_id))
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_permissions_assigned_to(self, *, role: Role) -> list[Permission]:
        """Get all permissions assigned to a specific role."""
        return role.permissions

    def get_permissions_assignable_to(self, *, role: Role) -> list[Permission]:
        """Get all permissions not assigned to the specified role."""
        stmt = select(Permission).join(RolePermission).filter(RolePermission.role_id != role.id)
        return list(self.db.execute(stmt).scalars().all())

    def deprecate(self, *, role: Role) -> Role:
        """Deprecate role by removing all user associations."""
        # Remove all user-role associations for this role
        user_role_associations = self.db.query(UserRole).filter(UserRole.role_id == role.id).all()
        for user_role_db in user_role_associations:
            self.db.delete(user_role_db)
        self.db.flush()
        return role

    def assign_permission(self, *, role: Role, permission: Permission) -> Role:
        """
        Assign a permission to a role. Idempotent operation.

        Args:
            role: The role to assign permission to
            permission: The permission to assign

        Returns:
            The updated role

        """
        # Check if association already exists
        existing = (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
            .one_or_none()
        )

        if existing is None:
            # Create new role-permission association
            role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
            self.db.add(role_permission)
            self.db.flush()

        return role

    def remove_permission(self, *, role: Role, permission: Permission) -> Role:
        """
        Remove a permission from a role. Idempotent operation.

        Args:
            role: The role to remove permission from
            permission: The permission to remove

        Returns:
            The updated role

        """
        # Find and remove the association
        association = (
            self.db.query(RolePermission)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
            .one_or_none()
        )

        if association is not None:
            self.db.delete(association)
            self.db.flush()

        return role

    def assign_user(self, *, role: Role, user: User) -> Role:
        """
        Assign a user to a role. Idempotent operation.

        Args:
            role: The role to assign user to
            user: The user to assign

        Returns:
            The updated role

        """
        # Check if association already exists
        existing = (
            self.db.query(UserRole)
            .filter(
                UserRole.role_id == role.id,
                UserRole.user_id == user.id,
            )
            .one_or_none()
        )

        if existing is None:
            # Create new user-role association
            user_role = UserRole(role_id=role.id, user_id=user.id)
            self.db.add(user_role)
            self.db.flush()

        return role

    def remove_user(self, *, role: Role, user: User) -> Role:
        """
        Remove a user from a role. Idempotent operation.

        Args:
            role: The role to remove user from
            user: The user to remove

        Returns:
            The updated role

        """
        # Find and remove the association
        association = (
            self.db.query(UserRole)
            .filter(
                UserRole.role_id == role.id,
                UserRole.user_id == user.id,
            )
            .one_or_none()
        )

        if association is not None:
            self.db.delete(association)
            self.db.flush()

        return role

    def remove_all_permissions(self, *, role: Role) -> Role:
        """
        Remove all permission associations from a role.

        Args:
            role: The role to remove all permissions from

        Returns:
            The updated role

        """
        # Remove all role-permission associations for this role
        permission_associations = self.db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        for role_permission in permission_associations:
            self.db.delete(role_permission)
        self.db.flush()
        return role


crud_roles = CRUDRole()

__all__ = ["crud_roles"]
