from kwik import models, schemas

from .auto_crud import AutoCRUD
from .roles_permissions import roles_permissions


class CRUDPermission(AutoCRUD[models.Permission, schemas.PermissionCreate, schemas.PermissionUpdate]):
    def get_by_name(self, *, name: str) -> models.Permission | None:
        return self.db.query(models.Permission).filter(models.Permission.name == name).one_or_none()

    @staticmethod
    def associate_role(
        *, role_db: models.Role, permission_db: models.Permission, creator_user: models.User
    ) -> models.Permission:
        role_permission_db = roles_permissions.get_by_permission_id_and_role_id(
            role_id=role_db.id, permission_id=permission_db.id
        )
        if role_permission_db is None:
            role_permission_in = schemas.role_permissions.RolePermissionCreate(
                role_id=role_db.id, permission_id=permission_db.id
            )
            roles_permissions.create(obj_in=role_permission_in, user=creator_user)

        return permission_db

    @staticmethod
    def purge_role(*, role_db: models.Role, permission_db: models.Permission) -> models.Permission:
        role_permission_db = roles_permissions.get_by_permission_id_and_role_id(
            role_id=role_db.id, permission_id=permission_db.id
        )
        roles_permissions.delete(obj_id=role_permission_db.id)
        return permission_db

    def deprecate(self, *, name: str) -> models.Permission:
        permission_db = self.get_by_name(name=name)
        r = roles_permissions.get_multi_by_permission_id(permission_id=permission_db.id)
        for role_permission_db in r:
            roles_permissions.delete(obj_id=role_permission_db.id)
        return permission_db


permission = CRUDPermission()
