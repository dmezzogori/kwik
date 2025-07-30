from kwik import models, schemas

from . import auto_crud


class AutoCRUDUserRoles(
    auto_crud.AutoCRUD[models.UserRole, schemas.UserRoleCreate, None],
):
    """CRUD operations for user-role associations and relationship management."""

    def get_by_user_id_and_role_id(
        self, *, user_id: int, role_id: int,
    ) -> models.UserRole | None:
        """Get user-role association by user ID and role ID."""
        return (
            self.db.query(models.UserRole)
            .filter(
                models.UserRole.user_id == user_id, models.UserRole.role_id == role_id,
            )
            .one_or_none()
        )

    def get_multi_by_role_id(self, *, role_id: int) -> list[models.UserRole]:
        """Get all user-role associations for a specific role."""
        return (
            self.db.query(models.UserRole)
            .filter(models.UserRole.role_id == role_id)
            .all()
        )


user_roles = AutoCRUDUserRoles()
