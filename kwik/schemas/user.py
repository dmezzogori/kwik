from pydantic import BaseModel, EmailStr

from .permission import PermissionORMSchema
from .role import Role


class UserBase(BaseModel):
    email: EmailStr | None = None
    is_active: bool | None = True
    is_superuser: bool | None = True


class UserCreate(UserBase):
    name: str
    surname: str
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    name: str | None = None
    surname: str | None = None


class UserChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserInDBBase(UserBase):
    id: int | None = None

    class Config:
        orm_mode = True


class User(UserInDBBase):
    name: str | None = None
    surname: str | None = None


class UserInDB(UserInDBBase):
    hashed_password: str


class UserWithPermissionsAndRoles(User):
    roles: list[Role]
    permissions: list[PermissionORMSchema]
