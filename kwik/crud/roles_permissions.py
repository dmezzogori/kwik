from kwik import models, schemas

from .auto_crud import AutoCRUD


class CRUDRolesPermissions(AutoCRUD[models.RolePermission, schemas.role_permissions.RolePermissionCreate, None]):
    def get_by_permission_id_and_role_id(self, *, permission_id: int, role_id: int) -> models.RolePermission | None:
        return (
            self.db.query(models.RolePermission)
            .filter(models.RolePermission.permission_id == permission_id, models.RolePermission.role_id == role_id)
            .one_or_none()
        )

    def get_multi_by_permission_id(self, *, permission_id: int) -> list[models.RolePermission]:
        return self.db.query(models.RolePermission).filter(models.RolePermission.permission_id == permission_id).all()


roles_permissions = CRUDRolesPermissions()
