from kwik import models, schemas

from . import auto_crud


class AutoCRUDUserRoles(auto_crud.AutoCRUD[models.UserRole, schemas.UserRoleCreate, None]):
    def get_by_user_id_and_role_id(self, *, user_id: int, role_id: int) -> models.UserRole | None:
        return (
            self.db.query(models.UserRole)
            .filter(models.UserRole.user_id == user_id, models.UserRole.role_id == role_id)
            .one_or_none()
        )

    def get_multi_by_role_id(self, *, role_id: int) -> list[models.UserRole]:
        return self.db.query(models.UserRole).filter(models.UserRole.role_id == role_id).all()


user_roles = AutoCRUDUserRoles()
