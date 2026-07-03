"""CRUD operations for users database entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel
from sqlalchemy import select

from kwik.exceptions import AuthenticationFailedError, InactiveUserError, UserNotFoundError
from kwik.models import User
from kwik.models.user_mixin import UserMixin
from kwik.security import get_password_hash, verify_password

from .autocrud import AutoCRUD
from .context import MaybeUserCtx

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kwik.models import Permission, Role
    from kwik.schemas import UserPasswordChange


class CRUDUsers[UserT: UserMixin](AutoCRUD[MaybeUserCtx, UserT, BaseModel, BaseModel, int]):
    """
    CRUD operations for user models with authentication and authorization support.

    Generic over the concrete user model; the kernel constructs it with the
    registered model: ``CRUDUsers(model=user_model)``.
    """

    # Expose only safe/public fields for list filtering/sorting
    list_allowed_fields: ClassVar[set[str]] = {"id", "name", "surname", "email", "is_active"}

    def get_by_email(self, *, email: str, context: MaybeUserCtx) -> UserT | None:
        """Get user by email address."""
        stmt = select(self.model).where(self.model.email == email)
        return context.session.execute(stmt).scalar_one_or_none()

    def create(self, *, obj_in: BaseModel, context: MaybeUserCtx) -> UserT:
        """
        Create new user with hashed password.

        Dumps the full registration payload so custom fields on extended user
        models flow into the model constructor; the plaintext ``password`` field
        is replaced by ``hashed_password``.
        """
        data = obj_in.model_dump()
        password = data.pop("password")
        db_obj = self.model(**data, hashed_password=get_password_hash(password))
        context.session.add(db_obj)
        context.session.flush()
        context.session.refresh(db_obj)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        obj_in: BaseModel,
        context: MaybeUserCtx,
        filters: dict[str, str],
        raise_on_error: bool = False,  # noqa: ARG002
    ) -> UserT:
        """Create user if it doesn't exist based on filters, otherwise return existing user."""
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)

        obj_db = context.session.execute(stmt).scalar_one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in, context=context)
        return obj_db

    def authenticate(self, *, email: str, password: str, context: MaybeUserCtx) -> UserT:
        """Authenticate a user with email and password."""
        user = self.get_by_email(email=email, context=context)

        # Check if the user exists and the password is correct
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationFailedError

        return user

    def change_password(self, *, user_id: int, obj_in: UserPasswordChange, context: MaybeUserCtx) -> UserT:
        """Change user password after validating old password."""
        user_db = self.get(entity_id=user_id, context=context)

        if not user_db:
            raise UserNotFoundError

        if not self.authenticate(email=user_db.email, password=obj_in.old_password, context=context):
            raise AuthenticationFailedError

        hashed_password = get_password_hash(obj_in.new_password)
        user_db.hashed_password = hashed_password

        return user_db

    def reset_password(self, *, email: str, password: str, context: MaybeUserCtx) -> UserT:
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

    def admin_reset_password(self, *, user_id: int, password: str, context: MaybeUserCtx) -> UserT:
        """Reset user password by user ID (admin operation, no old password required)."""
        user_db = self.get(entity_id=user_id, context=context)

        if user_db is None:
            raise UserNotFoundError

        self.is_active(user_db)

        user_db.hashed_password = get_password_hash(password)
        context.session.add(user_db)
        context.session.flush()

        return user_db

    @staticmethod
    def is_active(user: UserMixin) -> UserMixin:
        """Check if user is active, raise exception if not."""
        if not user.is_active:
            raise InactiveUserError
        return user

    def has_permissions(self, *, user: UserMixin, permissions: Sequence[str]) -> bool:
        """Check if the user has all the permissions provided."""
        user_permission_names = {permission.name for permission in user.permissions}
        return all(permission in user_permission_names for permission in permissions)

    def has_roles(self, *, user: UserMixin, roles: Sequence[str]) -> bool:
        """Check if the user has all the roles provided."""
        user_role_names = {role.name for role in user.roles}
        return all(role in user_role_names for role in roles)

    def get_permissions(self, *, user: UserMixin) -> list[Permission]:
        """Get all permissions given to the user."""
        return user.permissions

    def get_roles(self, *, user: UserMixin) -> list[Role]:
        """Get all roles associated to the user."""
        return user.roles


# TRANSITIONAL singleton (deleted in the router-factory task): keeps existing import
# sites working while internals migrate to get_kernel().crud_users.
crud_users = CRUDUsers(model=User)

__all__ = ["CRUDUsers", "crud_users"]
