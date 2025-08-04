"""CRUD operations for users database entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from starlette import status

from kwik import models, schemas
from kwik.core.security import get_password_hash, verify_password
from kwik.exceptions import IncorrectCredentials, UserInactive, UserNotFound

from . import auto_crud

if TYPE_CHECKING:
    from collections.abc import Sequence


class AutoCRUDUser(auto_crud.AutoCRUD[models.User, schemas.UserRegistration, schemas.UserProfileUpdate]):
    """CRUD operations for users with authentication and authorization support."""

    def get_by_email(self, *, email: str) -> models.User | None:
        """Get user by email address."""
        return self.db.query(models.User).filter(models.User.email == email).first()

    def get_by_name(self, *, name: str) -> models.User | None:
        """Get user by name."""
        return self.db.query(models.User).filter(models.User.name == name).first()

    # noinspection PyMethodOverriding
    def create(self, *, obj_in: schemas.UserRegistration) -> models.User:
        """Create new user with hashed password."""
        db_obj = models.User(
            name=obj_in.name,
            surname=obj_in.surname,
            email=obj_in.email,
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
            hashed_password=get_password_hash(obj_in.password),
        )
        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def create_if_not_exist(self, *, filters: dict, obj_in: schemas.UserRegistration) -> models.User:
        """Create user if it doesn't exist based on filters, otherwise return existing user."""
        obj_db = self.db.query(models.User).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in)
        return obj_db

    # noinspection PyMethodOverriding
    def update(self, *, db_obj: models.User, obj_in: schemas.UserProfileUpdate | dict[str, Any]) -> models.User:
        """Update user with password hashing support."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db_obj=db_obj, obj_in=update_data)

    def change_password(self, *, user_id: int, obj_in: schemas.UserPasswordChange) -> models.User:
        """Change user password after validating old password."""
        user_db = self.get(id=user_id)
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="The provided user does not exist",
            )
        if not self.authenticate(email=user_db.email, password=obj_in.old_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The provided password is wrong",
            )

        hashed_password = get_password_hash(obj_in.new_password)
        user_db.hashed_password = hashed_password
        return user_db

    def reset_password(self, *, email: str, password: str) -> models.User:
        """Reset user password by email."""
        user_db = self.get_by_email(email=email)
        if user_db is None:
            raise UserNotFound

        self.is_active(user_db)

        hashed_password = get_password_hash(password)
        user_db.hashed_password = hashed_password
        self.db.add(user_db)
        self.db.flush()
        return user_db

    def authenticate(self, *, email: str, password: str) -> models.User:
        """
        Authenticate a user with email and password.

        Raises:
            IncorrectCredentials: If the user does not exist or the password is wrong

        """
        # Retrieve the user from the database
        user_db = self.get_by_email(email=email)

        # Check if the user exists and the password is correct
        if user_db is None or not verify_password(password, user_db.hashed_password):
            raise IncorrectCredentials

        return user_db

    @staticmethod
    def is_active(user: models.User) -> models.User:
        """Check if user is active, raise exception if not."""
        if not user.is_active:
            raise UserInactive
        return user

    def is_superuser(self, *, user_id: int) -> bool:
        """Check if user has superuser privileges."""
        user_db = self.get_if_exist(id=user_id)
        return user_db.is_superuser

    def has_permissions(self, *, user_id: int, permissions: Sequence[str]) -> bool:
        """Check if the user has all the permissions provided."""
        r = (
            self.db.query(models.Permission)
            .join(models.RolePermission, models.Role, models.UserRole)
            .join(models.User, models.User.id == models.UserRole.user_id)
            .filter(
                models.Permission.name.in_(permissions),
                models.User.id == user_id,
            )
            .distinct()
        )
        return r.count() == len(permissions)

    def has_roles(self, *, user_id: int, roles: Sequence[str]) -> bool:
        """Check if the user has all the roles provided."""
        r = (
            self.db.query(models.Role)
            .join(models.UserRole, models.Role.id == models.UserRole.role_id)
            .join(models.User, models.User.id == models.UserRole.user_id)
            .filter(
                models.Role.name.in_(roles),
                models.User.id == user_id,
            )
            .distinct()
        )

        return r.count() == len(roles)

    def get_permissions(self, *, user_id: int) -> list[models.Permission]:
        """Get all permissions for a user through their roles."""
        return (
            self.db.query(models.Permission)
            .join(models.RolePermission, models.Role, models.UserRole)
            .join(models.User, models.User.id == models.UserRole.user_id)
            .filter(models.User.id == user_id)
            .distinct()
            .all()
        )


users = AutoCRUDUser()
