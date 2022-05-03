from typing import Optional

from pydantic import BaseModel


# Shared properties
class RoleBase(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = True


# Properties to receive via API on creation
class RoleCreate(RoleBase):
    name: str
    is_active: bool
    is_locked: bool


class UserRoleCreate(BaseModel):
    user_id: int
    role_id: int


class UserRoleRemove(UserRoleCreate):
    pass


# Properties to receive via API on update
class RoleUpdate(RoleBase):
    is_active: bool


class RoleInDBBase(RoleBase):
    id: Optional[int] = None

    class Config:
        orm_mode = True


# Additional properties to return via API
class Role(RoleInDBBase):
    pass


# Additional properties stored in DB
class RoleInDB(RoleInDBBase):
    pass


class RoleLookupSchema(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
