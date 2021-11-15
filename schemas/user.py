from typing import Optional, List

from pydantic import BaseModel, EmailStr

from .role import Role
from .permission import Permission

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True


# Properties to receive via API on creation
class UserCreate(UserBase):
    name: str
    surname: str
    email: EmailStr
    password: str


# Properties to receive via API on update
class UserUpdate(UserBase):
    name: Optional[str] = None
    surname: Optional[str] = None
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: Optional[int] = None

    class Config:
        orm_mode = True


# Additional properties to return via API
class User(UserInDBBase):
    name: Optional[str] = None
    surname: Optional[str] = None


# Additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str


class UserWithPermissionsAndRoles(User):
    roles: List[Role]
    permissions: List[Permission]
