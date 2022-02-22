from . import auto_crud
from .. import models
from ..database.session import KwikSession


class AutoCRUDRole(auto_crud.AutoCRUD):
    def get_by_name(self, *, db: KwikSession, name: str) -> models.Role | None:
        return db.query(models.Role).filter(models.Role.name == name).first()

    def get_multi_by_user_id(self, *, db: KwikSession, user_id: int) -> models.Role | None:
        return db.query(models.Role).join(models.UserRole).filter(models.UserRole.user_id == user_id).all()

    def get_users_by_name(self, db: KwikSession, *, name: str) -> list[models.User]:
        return (
            db.query(models.User)
            .join(models.UserRole, models.User.id == models.UserRole.user_id)
            .join(models.Role)
            .filter(models.Role.name == name)
            .all()
        )

    def get_users_by_role_id(self, db: KwikSession, *, role_id: int) -> list[models.User]:
        return (
            db.query(models.User)
            .join(models.UserRole, models.User.id == models.UserRole.user_id)
            .filter(models.UserRole.role_id == role_id)
            .all()
        )

    def get_users_not_in_role(self, db: KwikSession, *, role_id: int) -> list[models.User]:
        return (
            db.query(models.User)
            .join(models.UserRole, models.User.id == models.UserRole.user_id)
            .filter(models.UserRole.role_id != role_id)
            .all()
        )

    def get_permissions_not_in_role(self, db: KwikSession, *, role_id: int) -> models.Permission | None:
        return (
            db.query(models.Permission)
            .join(models.RolePermission)
            .filter(models.RolePermission.role_id != role_id)
            .all()
        )

    def get_permissions_by_role_id(self, db: KwikSession, *, role_id: int) -> list[models.Permission]:
        return (
            db.query(models.Permission)
            .join(models.RolePermission)
            .filter(models.RolePermission.role_id == role_id)
            .all()
        )

    def associate_user(
        self, *, db: KwikSession, role_db: models.Role, user_db: models.User, creator_user: models.User
    ) -> models.Role:
        user_role_db = (
            db.query(models.UserRole)
            .filter(models.UserRole.user_id == user_db.id, models.UserRole.role_id == role_db.id,)
            .one_or_none()
        )
        if user_role_db is None:
            user_role_db = models.UserRole(user_id=user_db.id, role_id=role_db.id, creator_user_id=creator_user.id)
            db.add(user_role_db)
            db.flush()
        return role_db

    def purge_user(self, *, db: KwikSession, role_db: models.Role, user_db: models.User) -> models.Role:
        user_role_db = (
            db.query(models.UserRole)
            .filter(models.UserRole.role_id == role_db.id, models.UserRole.user_id == user_db.id,)
            .first()
        )
        db.delete(user_role_db)
        db.flush()
        return role_db

    def deprecate(self, *, db: KwikSession, name: str) -> models.Role:
        role_db = self.get_by_name(db=db, name=name)
        r = db.query(models.UserRole).filter(models.UserRole.role_id == role_db.id).all()
        for user_role_db in r:
            db.delete(user_role_db)
        db.flush()
        return role_db

    def get_roles_lookup(self, *, db: KwikSession) -> list[models.Role]:
        return db.query(models.Role).all()


role = AutoCRUDRole(models.Role)
