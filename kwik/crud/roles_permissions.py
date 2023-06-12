from __future__ import annotations

import kwik.models
import kwik.schemas

from .auto_crud import AutoCRUD


class CRUDRolesPermissions(
    AutoCRUD[kwik.models.RolePermission, kwik.schemas.role_permissions.RolePermissionCreate, None]
):
    def get_by_permission_id_and_role_id(
        self, *, permission_id: int, role_id: int
    ) -> kwik.models.RolePermission | None:
        """
        Returns a single association between a permission and a role.
        """

        return (
            self.db.query(kwik.models.RolePermission)
            .filter(
                kwik.models.RolePermission.permission_id == permission_id,
                kwik.models.RolePermission.role_id == role_id,
            )
            .one_or_none()
        )

    def get_multi_by_permission_id(self, *, permission_id: int) -> list[kwik.models.RolePermission]:
        """
        Returns all associations of a permission.
        """

        return (
            self.db.query(kwik.models.RolePermission)
            .filter(kwik.models.RolePermission.permission_id == permission_id)
            .all()
        )


roles_permissions = CRUDRolesPermissions()
