from typing import Optional

from .base import CRUDBase

from sqlalchemy.orm import Session

from app.kwik.models.user import Role, User, UserRole
from app.kwik.schemas.role import RoleCreate, RoleUpdate

from app.kwik import models


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[Role]:
        return db.query(self.model).filter(self.model.name == name).first()

    def get_multi_by_user_id(self, db: Session, *, user_id: int) -> Optional[Role]:
        return db.query(self.model).join(UserRole).filter(UserRole.user_id == user_id).all()

    def get_users_by_name(self, db: Session, *, name: str) -> Optional[User]:
        return db.query(models.User).join(
            models.UserRole,
            models.Role
        ).filter(
            models.Role.name == name
        ).all()

    def associate_user(self, db: Session, *, role_db: models.Role, user_db: models.User) -> models.Role:
        user_role_db = models.UserRole(
            user_id=user_db.id,
            role_id=role_db.id
        )
        db.add(user_role_db)
        db.commit()
        return role_db

    def purge_user(self, db: Session, *, role_db: models.Role, user_db: models.User) -> models.Role:
        user_role_db = db.query(models.UserRole).filter(
            models.UserRole.role_id == role_db.id,
            models.UserRole.user_id == user_db.id
        ).first()
        db.delete(user_role_db)
        db.commit()
        return role_db

    def deprecate(self, db: Session, *, name: str) -> Role:
        role_db = self.get_by_name(db=db, name=name)
        r = db.query(models.UserRole).filter(
            models.UserRole.role_id == role_db.id
        ).all()
        for user_role_db in r:
            db.delete(user_role_db)
        db.commit()
        return role_db


role = CRUDRole(Role)
