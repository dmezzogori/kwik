from typing import Optional

from kwik.database.session import KwikSession
from kwik.models import Role, UserRole, User, Permission, RolePermission
from kwik.schemas import RoleCreate, RoleUpdate

from .auto_crud import AutoCRUD


class AutoCRUDRole(AutoCRUD):
    def get_by_name(self, *, db: KwikSession, name: str) -> Role | None:
        return db.query(Role).filter(Role.name == name).first()

    def get_multi_by_user_id(self, *, db: KwikSession, user_id: int) -> Role | None:
        return db.query(Role).join(UserRole).filter(UserRole.user_id == user_id).all()

    def get_users_by_name(self, db: KwikSession, *, name: str) -> list[User]:
        return (
            db.query(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role)
            .filter(Role.name == name)
            .all()
        )

    def get_users_by_role_id(self, db: KwikSession, *, role_id: int) -> list[User]:
        return (
            db.query(User)
            .join(UserRole, User.id == UserRole.user_id)
            .filter(UserRole.role_id == role_id)
            .all()
        )

    def get_users_not_in_role(self, db: KwikSession, *, role_id: int) -> list[User]:
        return (
            db.query(User)
            .join(UserRole, User.id == UserRole.user_id)
            .filter(UserRole.role_id != role_id)
            .all()
        )

    def get_permissions_not_in_role(
        self, db: KwikSession, *, role_id: int
    ) -> Optional[Permission]:
        return (
            db.query(Permission)
            .join(RolePermission)
            .filter(RolePermission.role_id != role_id)
            .all()
        )

    def get_permissions_by_role_id(
        self, db: KwikSession, *, role_id: int
    ) -> list[Permission]:
        return (
            db.query(Permission)
            .join(RolePermission)
            .filter(RolePermission.role_id == role_id)
            .all()
        )

    def associate_user(
        self, *, db: KwikSession, role_db: Role, user_db: User, creator_user: User
    ) -> Role:
        user_role_db = (
            db.query(UserRole)
            .filter(UserRole.user_id == user_db.id, UserRole.role_id == role_db.id,)
            .one_or_none()
        )
        if user_role_db is None:
            user_role_db = UserRole(
                user_id=user_db.id, role_id=role_db.id, creator_user_id=creator_user.id
            )
            db.add(user_role_db)
            db.flush()
        return role_db

    def purge_user(self, *, db: KwikSession, role_db: Role, user_db: User) -> Role:
        user_role_db = (
            db.query(UserRole)
            .filter(UserRole.role_id == role_db.id, UserRole.user_id == user_db.id,)
            .first()
        )
        db.delete(user_role_db)
        db.flush()
        return role_db

    def deprecate(self, *, db: KwikSession, name: str) -> Role:
        role_db = self.get_by_name(db=db, name=name)
        r = db.query(UserRole).filter(UserRole.role_id == role_db.id).all()
        for user_role_db in r:
            db.delete(user_role_db)
        db.flush()
        return role_db

    def get_roles_lookup(self, *, db: KwikSession) -> list[Role]:
        return db.query(Role).all()


role = AutoCRUDRole(Role)
