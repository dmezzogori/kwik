from __future__ import annotations

from pydantic import BaseModel, EmailStr

from .mixins import ORMMixin
from .permission import PermissionORMSchema
from .role import Role


class _BaseSchema(BaseModel):
    is_active: bool | None = True
    is_superuser: bool | None = True


class UserCreateSchema(_BaseSchema):
    name: str
    surname: str
    email: EmailStr
    password: str


class UserUpdateSchema(BaseModel):
    name: str | None = None
    surname: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


class UserChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str


class UserORMSchema(ORMMixin):
    name: str
    surname: str
    email: EmailStr


class UserORMExtendedSchema(UserORMSchema):
    roles: list[Role]
    permissions: list[PermissionORMSchema]
