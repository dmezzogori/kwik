"""CRUD operations for roles database entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import or_, select
from sqlalchemy.orm import undefer

from kwik.models import Permission, Role, RolePermission, User, UserRole
from kwik.schemas import RoleDefinition, RoleUpdate

from .autocrud import AutoCRUD
from .context import UserCtx

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from sqlalchemy.sql.base import ExecutableOption

    from kwik.models.base import Base


class CRUDRole(AutoCRUD[UserCtx, Role, RoleDefinition, RoleUpdate, int]):
    """CRUD operations for roles with user and permission management."""

    # Expose only safe/public fields for list filtering/sorting
    list_allowed_fields: ClassVar[set[str]] = {"id", "name", "is_active"}

    # Role reads serialize ``RoleProfile.user_count``; the column property is
    # deferred at the model level, so undefer it on the CRUD read paths.
    select_options: ClassVar[tuple[ExecutableOption, ...]] = (undefer(Role.user_count),)

    @staticmethod
    def _expire_loaded(*, session: Session, instance: Base, attributes: list[str]) -> None:
        """
        Expire attributes on an instance so stale viewonly caches reload on next access.

        The roles/users/permissions relationships are ``viewonly``: mutating the
        association rows directly does not update collections already loaded in the
        session. Expiring them after each association mutation keeps eager-loaded
        collections trustworthy within the same unit of work.

        Args:
            session: The active session.
            instance: The ORM instance whose attributes should be expired.
            attributes: Names of the attributes to expire.

        """
        if instance in session:
            session.expire(instance, attributes)

    def get_by_name(self, *, name: str, context: UserCtx) -> Role | None:
        """Get role by name."""
        stmt = select(Role).where(Role.name == name)
        return context.session.execute(stmt).scalar_one_or_none()

    def get_users_with(self, *, role: Role) -> list[User]:
        """Get all users associated with a specific role."""
        return role.users

    def get_users_without(self, *, role_id: int, context: UserCtx) -> list[User]:
        """Get all users not involved in the given role, including users with no role."""
        stmt = (
            select(User)
            .outerjoin(UserRole, User.id == UserRole.user_id)
            .filter(or_(UserRole.role_id.is_(None), UserRole.role_id != role_id))
        )
        return list(context.session.execute(stmt).scalars().all())

    def get_permissions_assigned_to(self, *, role: Role) -> list[Permission]:
        """Get all permissions assigned to a specific role."""
        return role.permissions

    def get_permissions_assignable_to(self, *, role: Role, context: UserCtx) -> list[Permission]:
        """Get all permissions not assigned to the specified role."""
        # Get all permissions that are NOT assigned to this specific role
        assigned_permission_ids = select(RolePermission.permission_id).filter(RolePermission.role_id == role.id)
        stmt = select(Permission).filter(Permission.id.not_in(assigned_permission_ids))
        return list(context.session.execute(stmt).scalars().all())

    def remove_all_users(self, *, role: Role, context: UserCtx) -> Role:
        """Remove all user associated with the role."""
        # Remove all user-role associations for this role
        user_role_associations = context.session.query(UserRole).filter(UserRole.role_id == role.id).all()
        removed_user_ids = {user_role_db.user_id for user_role_db in user_role_associations}
        for user_role_db in user_role_associations:
            context.session.delete(user_role_db)
        context.session.flush()
        self._expire_loaded(session=context.session, instance=role, attributes=["users", "user_count"])
        for obj in list(context.session.identity_map.values()):
            if isinstance(obj, User) and obj.id in removed_user_ids:
                self._expire_loaded(session=context.session, instance=obj, attributes=["roles"])
        return role

    def assign_permission(self, *, role: Role, permission: Permission, context: UserCtx) -> Role:
        """Assign a permission to a role. Idempotent operation."""
        # Check if association already exists
        existing = (
            context.session.query(RolePermission)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
            .one_or_none()
        )

        if existing is None:
            # Create new role-permission association
            role_permission = RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                creator_user_id=context.user.id,
            )
            context.session.add(role_permission)
            context.session.flush()
            self._expire_loaded(session=context.session, instance=role, attributes=["permissions"])
            self._expire_loaded(session=context.session, instance=permission, attributes=["roles"])

        return role

    def remove_permission(self, *, role: Role, permission: Permission, context: UserCtx) -> Role:
        """Remove a permission from a role. Idempotent operation."""
        # Find and remove the association
        association = (
            context.session.query(RolePermission)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
            .one_or_none()
        )

        if association is not None:
            context.session.delete(association)
            context.session.flush()
            self._expire_loaded(session=context.session, instance=role, attributes=["permissions"])
            self._expire_loaded(session=context.session, instance=permission, attributes=["roles"])

        return role

    def assign_user(self, *, role: Role, user: User, context: UserCtx) -> Role:
        """Assign a user to a role. Idempotent operation."""
        # Check if association already exists
        existing = (
            context.session.query(UserRole)
            .filter(
                UserRole.role_id == role.id,
                UserRole.user_id == user.id,
            )
            .one_or_none()
        )

        if existing is None:
            # Create new user-role association
            user_role = UserRole(
                role_id=role.id,
                user_id=user.id,
                creator_user_id=context.user.id,
            )
            context.session.add(user_role)
            context.session.flush()
            self._expire_loaded(session=context.session, instance=user, attributes=["roles"])
            self._expire_loaded(session=context.session, instance=role, attributes=["users", "user_count"])

        return role

    def remove_user(self, *, role: Role, user: User, context: UserCtx) -> Role:
        """Remove a user from a role. Idempotent operation."""
        # Find and remove the association
        association = (
            context.session.query(UserRole)
            .filter(
                UserRole.role_id == role.id,
                UserRole.user_id == user.id,
            )
            .one_or_none()
        )

        if association is not None:
            context.session.delete(association)
            context.session.flush()
            self._expire_loaded(session=context.session, instance=user, attributes=["roles"])
            self._expire_loaded(session=context.session, instance=role, attributes=["users", "user_count"])

        return role

    def remove_all_permissions(self, *, role: Role, context: UserCtx) -> Role:
        """Remove all permission associations from a role."""
        # Remove all role-permission associations for this role
        permission_associations = context.session.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        removed_permission_ids = {role_permission.permission_id for role_permission in permission_associations}
        for role_permission in permission_associations:
            context.session.delete(role_permission)
        context.session.flush()
        self._expire_loaded(session=context.session, instance=role, attributes=["permissions"])
        for obj in list(context.session.identity_map.values()):
            if isinstance(obj, Permission) and obj.id in removed_permission_ids:
                self._expire_loaded(session=context.session, instance=obj, attributes=["roles"])
        return role


crud_roles = CRUDRole()

__all__ = ["crud_roles"]
