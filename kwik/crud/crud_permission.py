from auto_crud import AutoCRUD
from kwik.database.session import KwikSession
from kwik.models import Permission, Role, User, RolePermission
from kwik.schemas import PermissionCreate, PermissionUpdate


class CRUDPermission(AutoCRUD[Permission, PermissionCreate, PermissionUpdate]):
    def get_by_name(self, *, db: KwikSession, name: str) -> Permission | None:
        return db.query(Permission).filter(Permission.name == name).one_or_none()

    def associate_role(
        self,
        *,
        db: KwikSession,
        role_db: Role,
        permission_db: Permission,
        creator_user: User
    ) -> Permission:
        role_permission_db = (
            db.query(RolePermission)
            .filter(
                RolePermission.permission_id == permission_db.id,
                RolePermission.role_id == role_db.id,
            )
            .one_or_none()
        )
        if role_permission_db is None:
            role_permission_db = RolePermission(
                permission_id=permission_db.id,
                role_id=role_db.id,
                creator_user_id=creator_user.id,
            )
            db.add(role_permission_db)
            db.flush()
        return permission_db

    def purge_role(
        self, *, db: KwikSession, role_db: Role, permission_db: Permission
    ) -> Permission:
        role_permission_db = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_db.id,
                RolePermission.permission_id == permission_db.id,
            )
            .first()
        )
        db.delete(role_permission_db)
        db.flush()
        return permission_db

    def deprecate(self, *, db: KwikSession, name: str) -> Permission:
        permission_db = self.get_by_name(db=db, name=name)
        r = (
            db.query(RolePermission)
            .filter(RolePermission.permission_id == permission_db.id)
            .all()
        )
        for role_permission_db in r:
            db.delete(role_permission_db)
        db.flush()
        return permission_db


permission = CRUDPermission(Permission)
