"""CRUD operations for users database entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import select
from starlette import status

from kwik.core.security import get_password_hash, verify_password
from kwik.crud import roles as crud_roles
from kwik.exceptions import AuthenticationFailedError, InactiveUserError, UserNotFoundError
from kwik.models import Permission, Role, RolePermission, User, UserRole
from kwik.schemas import UserPasswordChange, UserProfileUpdate, UserRegistration

from .auto_crud import AutoCRUD

if TYPE_CHECKING:
    from collections.abc import Sequence


class AutoCRUDUser(AutoCRUD[User, UserRegistration, UserProfileUpdate]):
    """CRUD operations for users with authentication and authorization support."""

    def get_by_email(self, *, email: str) -> User | None:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_name(self, *, name: str) -> User | None:
        """Get user by name."""
        stmt = select(User).where(User.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, *, obj_in: UserRegistration) -> User:
        """Create new user with hashed password."""
        db_obj = User(
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

    def create_if_not_exist(self, *, filters: dict, obj_in: UserRegistration) -> User:
        """Create user if it doesn't exist based on filters, otherwise return existing user."""
        stmt = select(User)
        for key, value in filters.items():
            stmt = stmt.where(getattr(User, key) == value)

        obj_db = self.db.execute(stmt).scalar_one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in)
        return obj_db

    def update(self, *, db_obj: User, obj_in: UserProfileUpdate | dict[str, Any]) -> User:
        """Update user with password hashing support."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db_obj=db_obj, obj_in=update_data)

    def change_password(self, *, user_id: int, obj_in: UserPasswordChange) -> User:
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

    def reset_password(self, *, email: str, password: str) -> User:
        """Reset user password by email."""
        user_db = self.get_by_email(email=email)
        if user_db is None:
            raise UserNotFoundError

        self.is_active(user_db)

        hashed_password = get_password_hash(password)
        user_db.hashed_password = hashed_password
        self.db.add(user_db)
        self.db.flush()
        return user_db

    def authenticate(self, *, email: str, password: str) -> User:
        """
        Authenticate a user with email and password.

        Raises:
            IncorrectCredentials: If the user does not exist or the password is wrong

        """
        # Retrieve the user from the database
        user_db = self.get_by_email(email=email)

        # Check if the user exists and the password is correct
        if user_db is None or not verify_password(password, user_db.hashed_password):
            raise AuthenticationFailedError

        return user_db

    @staticmethod
    def is_active(user: User) -> User:
        """Check if user is active, raise exception if not."""
        if not user.is_active:
            raise InactiveUserError
        return user

    def is_superuser(self, *, user_id: int) -> bool:
        """Check if user has superuser privileges."""
        user_db = self.get_if_exist(id=user_id)
        return user_db.is_superuser

    def has_permissions(self, *, user_id: int, permissions: Sequence[str]) -> bool:
        """Check if the user has all the permissions provided."""
        stmt = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .join(User, User.id == UserRole.user_id)
            .where(
                Permission.name.in_(permissions),
                User.id == user_id,
            )
            .distinct()
        )
        result = self.db.execute(stmt).scalars().all()
        return len(result) == len(permissions)

    def has_roles(self, *, user_id: int, roles: Sequence[str]) -> bool:
        """Check if the user has all the roles provided."""
        stmt = (
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .join(User, User.id == UserRole.user_id)
            .where(
                Role.name.in_(roles),
                User.id == user_id,
            )
            .distinct()
        )

        result = self.db.execute(stmt).scalars().all()
        return len(result) == len(roles)

    def get_permissions(self, *, user_id: int) -> list[Permission]:
        """Get all permissions for a user through their roles."""
        stmt = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .join(User, User.id == UserRole.user_id)
            .where(User.id == user_id)
            .distinct()
        )
        return list(self.db.execute(stmt).scalars().all())

    def _get_user_role_association(self, *, user_id: int, role_id: int) -> UserRole | None:
        """Get user-role association by user ID and role ID."""
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def assign_role(self, *, user_id: int, role_id: int) -> User:
        """Assign a role to a user. Idempotent operation."""
        # Verify user and role exist
        user_db = self.get_if_exist(id=user_id)

        crud_roles.get_if_exist(id=role_id)  # Verify role exists

        # Check if association already exists
        user_role_db = self._get_user_role_association(user_id=user_id, role_id=role_id)
        if user_role_db is None:
            # Create new user-role association with proper creator_user_id
            user_role_kwargs = {
                "user_id": user_id,
                "role_id": role_id,
            }

            # Set creator_user_id if current user is available (handles RecordInfoMixin requirement)
            if self.user is not None:
                user_role_kwargs["creator_user_id"] = self.user.id

            user_role_db = UserRole(**user_role_kwargs)
            self.db.add(user_role_db)
            self.db.flush()

        return user_db

    def remove_role(self, *, user_id: int, role_id: int) -> User:
        """Remove a role from a user. Idempotent operation."""
        # Verify user and role exist
        user_db = self.get_if_exist(id=user_id)

        crud_roles.get_if_exist(id=role_id)  # Verify role exists

        # Find and delete association if it exists
        user_role_db = self._get_user_role_association(user_id=user_id, role_id=role_id)
        if user_role_db is not None:
            self.db.delete(user_role_db)
            self.db.flush()

        return user_db

    def get_multi_by_role_name(self, *, role_name: str) -> list[User]:
        """Get all users assigned to a role by role name."""
        stmt = (
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.name == role_name)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_multi_by_role_id(self, *, role_id: int) -> list[User]:
        """Get all users assigned to a specific role."""
        stmt = select(User).join(UserRole, User.id == UserRole.user_id).where(UserRole.role_id == role_id)
        return list(self.db.execute(stmt).scalars().all())


users = AutoCRUDUser()
