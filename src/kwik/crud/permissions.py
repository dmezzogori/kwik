"""CRUD operations for permissions database entities."""

from __future__ import annotations

from kwik import crud, models, schemas

from .auto_crud import AutoCRUD


class CRUDPermission(AutoCRUD[models.Permission, schemas.PermissionDefinition, schemas.PermissionUpdate]):
    """CRUD operations for permissions with role association management."""

    def get_by_name(self, *, name: str) -> models.Permission | None:
        """Get a permission by name, if any."""
        return self.db.query(models.Permission).filter(models.Permission.name == name).one_or_none()

    def _get_permission_role_association(self, *, permission_id: int, role_id: int) -> models.RolePermission | None:
        """Get a single association between a permission and a role."""
        return (
            self.db.query(models.RolePermission)
            .filter(
                models.RolePermission.permission_id == permission_id,
                models.RolePermission.role_id == role_id,
            )
            .one_or_none()
        )

    def _get_role_associations(self, *, permission_id: int) -> list[models.RolePermission]:
        """Get all associations of a permission."""
        return self.db.query(models.RolePermission).filter(models.RolePermission.permission_id == permission_id).all()

    def associate_role(self, *, role_id: int, permission_id: int) -> models.Permission:
        """
        Associate a permission to a role. Idempotent operation.

        Raises:
            NotFound: If the provided permission or role does not exist

        """
        permission = self.get_if_exist(id=permission_id)
        role = crud.roles.get_if_exist(id=role_id)

        role_permission_db = self._get_permission_role_association(
            role_id=role.id,
            permission_id=permission.id,
        )
        if role_permission_db is None:
            # Create new role-permission association
            role_permission_db = models.RolePermission(role_id=role.id, permission_id=permission.id)
            self.db.add(role_permission_db)
            self.db.flush()

        return permission

    def purge_role(self, *, role_id: int, permission_id: int) -> models.Permission:
        """
        Remove the association between a permission and a role. Idempotent operation.

        Raises:
            NotFound: If the provided permission or role does not exist

        """
        permission = self.get_if_exist(id=permission_id)
        role = crud.roles.get_if_exist(id=role_id)

        role_permission_db = self._get_permission_role_association(
            role_id=role.id,
            permission_id=permission.id,
        )
        if role_permission_db is not None:
            self.db.delete(role_permission_db)
            self.db.flush()

        return permission

    def purge_all_roles(self, *, permission_id: int) -> models.Permission:
        """
        Deprecate a permission by name.

        Raises:
            NotFound: If the provided permission does not exist

        """
        # Retrieve the permission
        permission: models.Permission = self.get_if_exist(id=permission_id)

        # Retrieve all the roles associated with the permission
        for role_permission_db in self._get_role_associations(permission_id=permission.id):
            # Remove the association between the permission and the role
            self.db.delete(role_permission_db)

        self.db.flush()
        return permission

    def delete(self, *, permission_id: int) -> models.Permission:
        """
        Delete a permission by id.

        Remove all the associations between the permission and the roles associated with it.

        Raises:
            NotFound: If the provided permission does not exist

        """
        self.purge_all_roles(permission_id=permission_id)
        return super().delete(id=permission_id)

    def get_multi_by_role_id(self, *, role_id: int) -> list[models.Permission]:
        """Get all permissions assigned to a specific role."""
        return (
            self.db.query(models.Permission)
            .join(models.RolePermission)
            .filter(models.RolePermission.role_id == role_id)
            .all()
        )


permissions = CRUDPermission()
