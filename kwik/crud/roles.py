from kwik import models, schemas

from .auto_crud import AutoCRUD
from .user_roles import user_roles


class AutoCRUDRole(AutoCRUD[models.Role, schemas.RoleCreate, schemas.RoleUpdate]):
    def get_by_name(self, *, name: str) -> models.Role | None:
        return self.db.query(models.Role).filter(models.Role.name == name).first()

    def get_multi_by_user_id(self, *, user_id: int) -> list[models.Role]:
        return self.db.query(models.Role).join(models.UserRole).filter(models.UserRole.user_id == user_id).all()

    def get_users_by_name(self, *, name: str) -> list[models.User]:
        # TODO: va sostituita con un metodo sul crud degli utenti
        #  crud.users.get_multi_by_role_name(name=name)
        return (
            self.db.query(models.User)
            .join(models.UserRole, models.User.id == models.UserRole.user_id)
            .join(models.Role)
            .filter(models.Role.name == name)
            .all()
        )

    def get_users_by_role_id(self, *, role_id: int) -> list[models.User]:
        # TODO: va sostituita con un metodo sul crud degli utenti
        return (
            self.db.query(models.User)
            .join(models.UserRole, models.User.id == models.UserRole.user_id)
            .filter(models.UserRole.role_id == role_id)
            .all()
        )

    def get_users_not_in_role(self, *, role_id: int) -> list[models.User]:
        # TODO: va sostituita con un metodo sul crud degli utenti
        return (
            self.db.query(models.User)
            .join(models.UserRole, models.User.id == models.UserRole.user_id)
            .filter(models.UserRole.role_id != role_id)
            .all()
        )

    def get_permissions_not_in_role(self, *, role_id: int) -> list[models.Permission]:
        # TODO: va sostituita con un metodo sul crud dei permessi
        return (
            self.db.query(models.Permission)
            .join(models.RolePermission)
            .filter(models.RolePermission.role_id != role_id)
            .all()
        )

    def get_permissions_by_role_id(self, *, role_id: int) -> list[models.Permission]:
        # TODO: va sostituita con un metodo sul crud dei permessi
        return (
            self.db.query(models.Permission)
            .join(models.RolePermission)
            .filter(models.RolePermission.role_id == role_id)
            .all()
        )

    @staticmethod
    def associate_user(*, role_db: models.Role, user_db: models.User) -> models.Role:
        user_role_db = user_roles.get_by_user_id_and_role_id(user_id=user_db.id, role_id=role_db.id)
        if user_role_db is None:
            user_role_in = schemas.UserRoleCreate(
                user_id=user_db.id,
                role_id=role_db.id,
            )
            user_roles.create(obj_in=user_role_in)
        return role_db

    @staticmethod
    def purge_user(*, role_db: models.Role, user_db: models.User) -> models.Role:
        user_role_db = user_roles.get_by_user_id_and_role_id(user_id=user_db.id, role_id=role_db.id)
        user_roles.delete(id=user_role_db.id)
        return role_db

    def deprecate(self, *, name: str) -> models.Role:
        role_db = self.get_by_name(name=name)
        user_roles_db = user_roles.get_multi_by_role_id(role_id=role_db.id)
        for user_role_db in user_roles_db:
            user_roles.delete(id=user_role_db.id)
        return role_db


role = AutoCRUDRole()
