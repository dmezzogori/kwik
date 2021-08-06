from typing import Optional

from sqlalchemy.orm import Session

from app.kwik import models, schemas
from .base import CRUDBase


class CRUDRole(CRUDBase[models.Role, schemas.RoleCreate, schemas.RoleUpdate]):
    def get_by_name(self, *, db: Session, name: str) -> Optional[models.Role]:
        return db.query(self.model).filter(self.model.name == name).first()

    def get_multi_by_user_id(self, *, db: Session, user_id: int) -> Optional[models.Role]:
        return db.query(self.model).join(models.UserRole).filter(models.UserRole.user_id == user_id).all()

    def get_users_by_name(self, db: Session, *, name: str) -> Optional[models.User]:
        return db.query(models.User).join(models.UserRole, models.User.id == models.UserRole.user_id).join(models.Role).filter(models.Role.name == name).all()

    def get_users_not_in_role(self, db: Session, *, role_id: int) -> Optional[models.User]:
        return db.query(models.User).join(models.UserRole, models.User.id == models.UserRole.user_id).filter(models.UserRole.role_id != role_id).all()

    def associate_user(
        self, *, db: Session, role_db: models.Role, user_db: models.User, creator_user: models.User
    ) -> models.Role:
        user_role_db = (
            db.query(models.UserRole)
            .filter(models.UserRole.user_id == user_db.id, models.UserRole.role_id == role_db.id)
            .one_or_none()
        )
        if user_role_db is None:
            user_role_db = models.UserRole(user_id=user_db.id, role_id=role_db.id, creator_user_id=creator_user.id)
            db.add(user_role_db)
            db.flush()
        return role_db

    def purge_user(self, *, db: Session, role_db: models.Role, user_db: models.User) -> models.Role:
        user_role_db = (
            db.query(models.UserRole)
            .filter(models.UserRole.role_id == role_db.id, models.UserRole.user_id == user_db.id,)
            .first()
        )
        db.delete(user_role_db)
        db.flush()
        return role_db

    def deprecate(self, *, db: Session, name: str) -> models.Role:
        role_db = self.get_by_name(db=db, name=name)
        r = db.query(models.UserRole).filter(models.UserRole.role_id == role_db.id).all()
        for user_role_db in r:
            db.delete(user_role_db)
        db.flush()
        return role_db


role = CRUDRole(models.Role)
