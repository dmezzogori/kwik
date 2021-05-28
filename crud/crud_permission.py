from typing import Optional

from .base import CRUDBase

from sqlalchemy.orm import Session

from app.kwik.models.user import Permission, User
from app.kwik.schemas.permission import PermissionCreate, PermissionUpdate

from app.kwik import models


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Permission]:
        return db.query(self.model).filter(self.model.name == name).first()

    def associate_role(self, db: Session, *, role_db: models.Role, permission_db: models.Permission) -> models.Permission:
        role_permission_db = models.RolePermission(
            permission_id=user_db.id,
            role_id=role_db.id
        )
        db.add(role_permission_db)
        db.commit()
        return permission_db

    def purge_role(self, db: Session, *, role_db: models.Role, permission_db: models.Permission) -> models.Permission:
        role_permission_db = db.query(models.RolePermission).filter(
            models.RolePermission.role_id == role_db.id,
            models.RolePermission.permission_id == permission_db.id
        ).first()
        db.delete(role_permission_db)
        db.commit()
        return permission_db

    def deprecate(self, db: Session, *, name: str) -> models.Permission:
        permission_db = self.get_by_name(db=db, name=name)
        r = db.query(models.RolePermission).filter(
            models.RolePermission.permission_id == permission_db.id
        ).all()
        for role_permission_db in r:
            db.delete(role_permission_db)
        db.commit()
        return permission_db


permission = CRUDPermission(Permission)
