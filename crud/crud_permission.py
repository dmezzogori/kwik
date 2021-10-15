from typing import Optional

from sqlalchemy.orm import Session

from kwik import models, schemas
from .base import CRUDBase


class CRUDPermission(CRUDBase[models.Permission, schemas.PermissionCreate, schemas.PermissionUpdate]):
    def get_by_name(self, *, db: Session, name: str) -> Optional[models.Permission]:
        return db.query(self.model).filter(self.model.name == name).first()

    def associate_role(
        self, *, db: Session, role_db: models.Role, permission_db: models.Permission, creator_user: models.User
    ) -> models.Permission:
        role_permission_db = (
            db.query(models.RolePermission)
            .filter(
                models.RolePermission.permission_id == permission_db.id, models.RolePermission.role_id == role_db.id
            )
            .one_or_none()
        )
        if role_permission_db is None:
            role_permission_db = models.RolePermission(
                permission_id=permission_db.id, role_id=role_db.id, creator_user_id=creator_user.id
            )
            db.add(role_permission_db)
            db.flush()
        return permission_db

    def purge_role(self, *, db: Session, role_db: models.Role, permission_db: models.Permission) -> models.Permission:
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

    def deprecate(self, *, db: Session, name: str) -> models.Permission:
        permission_db = self.get_by_name(db=db, name=name)
        r = db.query(models.RolePermission).filter(models.RolePermission.permission_id == permission_db.id).all()
        for role_permission_db in r:
            db.delete(role_permission_db)
        db.flush()
        return permission_db


permission = CRUDPermission(models.Permission)
