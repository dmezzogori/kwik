"""CRUD operations for permissions database entities."""

from __future__ import annotations

from sqlalchemy import select

from kwik.models import Permission, Role, RolePermission
from kwik.schemas import PermissionDefinition, PermissionUpdate

from .autocrud import AutoCRUD, UserCtx
from .roles import crud_roles


class CRUDPermission(AutoCRUD[UserCtx, Permission, PermissionDefinition, PermissionUpdate]):
    """CRUD operations for permissions with role association management."""

    def get_by_name(self, *, name: str, context: UserCtx) -> Permission | None:
        """Get a permission by name, if any."""
        return context.session.query(Permission).filter(Permission.name == name).one_or_none()

    def _get_permission_role_association(
        self, *, permission_id: int, role_id: int, context: UserCtx
    ) -> RolePermission | None:
        """Get a single association between a permission and a role."""
        return (
            context.session.query(RolePermission)
            .filter(
                RolePermission.permission_id == permission_id,
                RolePermission.role_id == role_id,
            )
            .one_or_none()
        )

    def _get_role_associations(self, *, permission_id: int, context: UserCtx) -> list[RolePermission]:
        """Get all associations of a permission."""
        return context.session.query(RolePermission).filter(RolePermission.permission_id == permission_id).all()

    def associate_role(self, *, role_id: int, permission_id: int, context: UserCtx) -> Permission:
        """
        Associate a permission to a role. Idempotent operation.

        Raises:
            NotFound: If the provided permission or role does not exist

        """
        permission = self.get_if_exist(id=permission_id, context=context)
        role = crud_roles.get_if_exist(id=role_id, context=context)

        role_permission_db = self._get_permission_role_association(
            role_id=role.id, permission_id=permission.id, context=context
        )
        if role_permission_db is None:
            # Create new role-permission association
            role_permission_db = RolePermission(role_id=role.id, permission_id=permission.id)
            context.session.add(role_permission_db)
            context.session.flush()

        return permission

    def purge_role(self, *, role_id: int, permission_id: int, context: UserCtx) -> Permission:
        """
        Remove the association between a permission and a role. Idempotent operation.

        Raises:
            NotFound: If the provided permission or role does not exist

        """
        permission = self.get_if_exist(id=permission_id, context=context)
        role = crud_roles.get_if_exist(id=role_id, context=context)

        role_permission_db = self._get_permission_role_association(
            role_id=role.id, permission_id=permission.id, context=context
        )
        if role_permission_db is not None:
            context.session.delete(role_permission_db)
            context.session.flush()

        return permission

    def purge_all_roles(self, *, permission_id: int, context: UserCtx) -> Permission:
        """
        Deprecate a permission by name.

        Raises:
            NotFound: If the provided permission does not exist

        """
        # Retrieve the permission
        permission: Permission = self.get_if_exist(id=permission_id, context=context)

        # Retrieve all the roles associated with the permission
        for role_permission_db in self._get_role_associations(permission_id=permission.id, context=context):
            # Remove the association between the permission and the role
            context.session.delete(role_permission_db)

        context.session.flush()
        return permission

    def delete(self, *, permission_id: int, context: UserCtx) -> Permission | None:
        """
        Delete a permission by id.

        Remove all the associations between the permission and the roles associated with it.

        Raises:
            NotFound: If the provided permission does not exist

        """
        self.purge_all_roles(permission_id=permission_id, context=context)
        return super().delete(id=permission_id, context=context)

    def get_roles_assigned_to(self, *, permission: Permission) -> list[Role]:
        """Get all roles that have been assigned to a specific permission."""
        return permission.roles

    def get_roles_assignable_to(self, *, permission: Permission, context: UserCtx) -> list[Role]:
        """Get all roles not assigned to the specified permission."""
        stmt = select(Role).join(RolePermission).filter(RolePermission.permission_id != permission.id)
        return list(context.session.execute(stmt).scalars().all())


crud_permissions = CRUDPermission()


__all__ = ["crud_permissions"]
