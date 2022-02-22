from . import auto_crud
from .. import models
from ..database.session import KwikSession


class CRUDPermission(auto_crud.AutoCRUD):
    def get_by_name(self, *, db: KwikSession, name: str) -> models.Permission | None:
        return db.query(models.Permission).filter(models.Permission.name == name).one_or_none()

    def associate_role(
        self, *, db: KwikSession, role_db: models.Role, permission_db: models.Permission, creator_user: models.User
    ) -> models.Permission:
        role_permission_db = (
            db.query(models.RolePermission)
            .filter(
                models.RolePermission.permission_id == permission_db.id, models.RolePermission.role_id == role_db.id,
            )
            .one_or_none()
        )
        if role_permission_db is None:
            role_permission_db = models.RolePermission(
                permission_id=permission_db.id, role_id=role_db.id, creator_user_id=creator_user.id,
            )
            db.add(role_permission_db)
            db.flush()
        return permission_db

    def purge_role(
        self, *, db: KwikSession, role_db: models.Role, permission_db: models.Permission
    ) -> models.Permission:
        role_permission_db = (
            db.query(models.RolePermission)
            .filter(
                models.RolePermission.role_id == role_db.id, models.RolePermission.permission_id == permission_db.id,
            )
            .first()
        )
        db.delete(role_permission_db)
        db.flush()
        return permission_db

    def deprecate(self, *, db: KwikSession, name: str) -> models.Permission:
        permission_db = self.get_by_name(db=db, name=name)
        r = db.query(models.RolePermission).filter(models.RolePermission.permission_id == permission_db.id).all()
        for role_permission_db in r:
            db.delete(role_permission_db)
        db.flush()
        return permission_db


permission = CRUDPermission(models.Permission)
