"""Pydantic schemas for user validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr

from .mixins import ORMMixin

if TYPE_CHECKING:
    from .permission import PermissionORMSchema
    from .role import Role


class _BaseSchema(BaseModel):
    is_active: bool | None = True
    is_superuser: bool | None = True


class UserCreateSchema(_BaseSchema):
    """Schema for creating new users with required fields."""

    name: str
    surname: str
    email: EmailStr
    password: str


class UserUpdateSchema(BaseModel):
    """Schema for updating existing user information."""

    name: str | None = None
    surname: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


class UserChangePasswordSchema(BaseModel):
    """Schema for user password change requests."""

    old_password: str
    new_password: str


class UserORMSchema(ORMMixin):
    """ORM schema for user data with database ID."""

    name: str
    surname: str
    email: EmailStr


class UserORMExtendedSchema(UserORMSchema):
    """Extended user ORM schema including roles and permissions."""

    roles: list[Role]
    permissions: list[PermissionORMSchema]
