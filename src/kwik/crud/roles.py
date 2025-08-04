"""CRUD operations for roles database entities."""

from __future__ import annotations

from sqlalchemy import or_

from kwik import models, schemas

from .auto_crud import AutoCRUD


class AutoCRUDRole(AutoCRUD[models.Role, schemas.RoleDefinition, schemas.RoleUpdate]):
    """CRUD operations for roles with user and permission management."""

    def get_by_name(self, *, name: str) -> models.Role | None:
        """Get role by name."""
        return self.db.query(models.Role).filter(models.Role.name == name).first()

    def get_multi_by_user_id(self, *, user_id: int) -> list[models.Role]:
        """Get all roles assigned to a specific user."""
        return self.db.query(models.Role).join(models.UserRole).filter(models.UserRole.user_id == user_id).all()


    def get_users_not_in_role(self, *, role_id: int) -> list[models.User]:
        """Get all users not involved in the given role, including users with no role."""
        return (
            self.db.query(models.User)
            .outerjoin(models.UserRole, models.User.id == models.UserRole.user_id)
            .filter(or_(models.UserRole.role_id.is_(None), models.UserRole.role_id != role_id))
            .all()
        )

    def get_permissions_not_assigned_to_role(self, *, role_id: int) -> list[models.Permission]:
        """Get all permissions not assigned to the specified role."""
        return (
            self.db.query(models.Permission)
            .join(models.RolePermission)
            .filter(models.RolePermission.role_id != role_id)
            .all()
        )


    def deprecate(self, *, name: str) -> models.Role:
        """Deprecate role by removing all user associations."""
        role_db = self.get_by_name(name=name)
        # Remove all user-role associations for this role
        user_role_associations = (
            self.db.query(models.UserRole)
            .filter(models.UserRole.role_id == role_db.id)
            .all()
        )
        for user_role_db in user_role_associations:
            self.db.delete(user_role_db)
        self.db.flush()
        return role_db


roles = AutoCRUDRole()
