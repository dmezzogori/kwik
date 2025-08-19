"""CRUD operations for permissions database entities."""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy import select

from kwik.models import Permission, Role, RolePermission
from kwik.schemas import PermissionDefinition, PermissionUpdate

from .autocrud import AutoCRUD
from .context import UserCtx


class CRUDPermission(AutoCRUD[UserCtx, Permission, PermissionDefinition, PermissionUpdate, int]):
    """CRUD operations for permissions with role association management."""

    # Expose only safe/public fields for list filtering/sorting
    list_allowed_fields: ClassVar[set[str]] = {"id", "name"}

    def get_by_name(self, *, name: str, context: UserCtx) -> Permission | None:
        """Get a permission by name, if any."""
        return context.session.query(Permission).filter(Permission.name == name).one_or_none()

    def _get_role_associations(self, *, permission_id: int, context: UserCtx) -> list[RolePermission]:
        """Get all associations of a permission."""
        return context.session.query(RolePermission).filter(RolePermission.permission_id == permission_id).all()

    def purge_all_roles(self, *, permission_id: int, context: UserCtx) -> Permission:
        """
        Deprecate a permission by name.

        Raises:
            NotFound: If the provided permission does not exist

        """
        # Retrieve the permission
        permission = self.get_if_exist(entity_id=permission_id, context=context)

        # Retrieve all the roles associated with the permission
        for role_permission_db in self._get_role_associations(permission_id=permission.id, context=context):
            # Remove the association between the permission and the role
            context.session.delete(role_permission_db)

        context.session.flush()
        return permission

    def delete(self, *, entity_id: int, context: UserCtx) -> Permission:
        """
        Delete a permission by id.

        Remove all the associations between the permission and the roles associated with it.

        Raises:
            NotFound: If the provided permission does not exist

        """
        self.purge_all_roles(permission_id=entity_id, context=context)
        return super().delete(entity_id=entity_id, context=context)

    def get_roles_assigned_to(self, *, permission: Permission) -> list[Role]:
        """Get all roles that have been assigned to a specific permission."""
        return permission.roles

    def get_roles_assignable_to(self, *, permission: Permission, context: UserCtx) -> list[Role]:
        """Get all roles not assigned to the specified permission."""
        # Get all roles that do not have a role-permission association with this permission
        assigned_role_ids_subq = select(RolePermission.role_id).where(RolePermission.permission_id == permission.id)
        stmt = select(Role).where(Role.id.notin_(assigned_role_ids_subq))
        return list(context.session.execute(stmt).scalars().all())


crud_permissions = CRUDPermission()


__all__ = ["crud_permissions"]
