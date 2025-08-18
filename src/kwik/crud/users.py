"""CRUD operations for users database entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import select

from kwik.exceptions import AuthenticationFailedError, InactiveUserError, UserNotFoundError
from kwik.models import Permission, Role, User
from kwik.schemas import UserPasswordChange, UserProfileUpdate, UserRegistration
from kwik.security import get_password_hash, verify_password

from .autocrud import AutoCRUD
from .context import MaybeUserCtx

if TYPE_CHECKING:
    from collections.abc import Sequence


class _CRUDUsers(AutoCRUD[MaybeUserCtx, User, UserRegistration, UserProfileUpdate, int]):
    """CRUD operations for users with authentication and authorization support."""

    # Expose only safe/public fields for list filtering/sorting
    list_allowed_fields: ClassVar[set[str]] = {"id", "name", "surname", "email", "is_active"}

    def get_by_email(self, *, email: str, context: MaybeUserCtx) -> User | None:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        return context.session.execute(stmt).scalar_one_or_none()

    def create(self, *, obj_in: UserRegistration, context: MaybeUserCtx) -> User:
        """
        Create new user with hashed password.

        This method overrides the superclass to ensure that the user's password
        is securely hashed before being stored in the database. The base class
        does not handle password hashing, so this override is necessary for
        proper security.
        """
        db_obj = User(
            name=obj_in.name,
            surname=obj_in.surname,
            email=obj_in.email,
            is_active=obj_in.is_active,
            hashed_password=get_password_hash(obj_in.password),
        )
        context.session.add(db_obj)
        context.session.flush()
        context.session.refresh(db_obj)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        obj_in: UserRegistration,
        context: MaybeUserCtx,
        filters: dict[str, str],
        raise_on_error: bool = False,  # noqa: ARG002
    ) -> User:
        """Create user if it doesn't exist based on filters, otherwise return existing user."""
        stmt = select(User)
        for key, value in filters.items():
            stmt = stmt.where(getattr(User, key) == value)

        obj_db = context.session.execute(stmt).scalar_one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in, context=context)
        return obj_db

    def authenticate(self, *, email: str, password: str, context: MaybeUserCtx) -> User:
        """Authenticate a user with email and password."""
        user = self.get_by_email(email=email, context=context)

        # Check if the user exists and the password is correct
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationFailedError

        return user

    def change_password(self, *, user_id: int, obj_in: UserPasswordChange, context: MaybeUserCtx) -> User:
        """Change user password after validating old password."""
        user_db = self.get(entity_id=user_id, context=context)

        if not user_db:
            raise UserNotFoundError

        if not self.authenticate(email=user_db.email, password=obj_in.old_password, context=context):
            raise AuthenticationFailedError

        hashed_password = get_password_hash(obj_in.new_password)
        user_db.hashed_password = hashed_password

        return user_db

    def reset_password(self, *, email: str, password: str, context: MaybeUserCtx) -> User:
        """Reset user password by email."""
        user_db = self.get_by_email(email=email, context=context)

        if user_db is None:
            raise UserNotFoundError

        self.is_active(user_db)

        hashed_password = get_password_hash(password)
        user_db.hashed_password = hashed_password
        context.session.add(user_db)
        context.session.flush()

        return user_db

    @staticmethod
    def is_active(user: User) -> User:
        """Check if user is active, raise exception if not."""
        if not user.is_active:
            raise InactiveUserError
        return user

    def has_permissions(self, *, user: User, permissions: Sequence[str]) -> bool:
        """Check if the user has all the permissions provided."""
        user_permission_names = {permission.name for permission in user.permissions}
        return all(permission in user_permission_names for permission in permissions)

    def has_roles(self, *, user: User, roles: Sequence[str]) -> bool:
        """Check if the user has all the roles provided."""
        user_role_names = {role.name for role in user.roles}
        return all(role in user_role_names for role in roles)

    def get_permissions(self, *, user: User) -> list[Permission]:
        """Get all permissions given to the user."""
        return user.permissions

    def get_roles(self, *, user: User) -> list[Role]:
        """Get all roles associated to the user."""
        return user.roles


crud_users = _CRUDUsers()

__all__ = ["crud_users"]
