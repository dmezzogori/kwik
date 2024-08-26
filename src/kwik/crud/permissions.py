from __future__ import annotations

from kwik import crud, models, schemas

from .auto_crud import AutoCRUD
from .roles_permissions import roles_permissions


class CRUDPermission(AutoCRUD[models.Permission, schemas.PermissionCreate, schemas.PermissionUpdate]):
    def get_by_name(self, *, name: str) -> models.Permission | None:
        """
        Get a permission by name, if any.
        """

        return self.db.query(models.Permission).filter(models.Permission.name == name).one_or_none()

    def associate_role(self, *, role_id: int, permission_id: int) -> models.Permission:
        """
        Associate a permission to a role. Idempotent operation.

        Raises:
            NotFound: If the provided permission or role does not exist
        """

        permission = self.get_if_exist(id=permission_id)
        role = crud.role.get_if_exist(id=role_id)

        role_permission_db = roles_permissions.get_by_permission_id_and_role_id(
            role_id=role.id, permission_id=permission.id
        )
        if role_permission_db is None:
            roles_permissions.create(
                obj_in=schemas.role_permissions.RolePermissionCreate(role_id=role.id, permission_id=permission.id)
            )

        return permission

    def purge_role(self, *, role_id: int, permission_id: int) -> models.Permission:
        """
        Remove the association between a permission and a role. Idempotent operation.

        Raises:
            NotFound: If the provided permission or role does not exist
        """

        permission = self.get_if_exist(id=permission_id)
        role = crud.role.get_if_exist(id=role_id)

        role_permission_db = roles_permissions.get_by_permission_id_and_role_id(
            role_id=role.id, permission_id=permission.id
        )
        if role_permission_db is not None:
            roles_permissions.delete(id=role_permission_db.id)

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
        for role_permission_db in roles_permissions.get_multi_by_permission_id(permission_id=permission.id):
            # Remove the association between the permission and the role
            roles_permissions.delete(obj_id=role_permission_db.id)

        return permission

    def delete(self, *, id: int) -> models.Permission:
        """
        Delete a permission by id.
        Remove all the associations between the permission and the roles associated with it.

        Raises:
            NotFound: If the provided permission does not exist
        """

        self.purge_all_roles(permission_id=id)
        return super().delete(id=id)


permission = CRUDPermission()
