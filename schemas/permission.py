from typing import Optional

from pydantic import BaseModel


# Shared properties
class PermissionBase(BaseModel):
    name: Optional[str] = None


# Properties to receive via API on creation
class PermissionCreate(PermissionBase):
    name: str


class PermissionRoleCreate(BaseModel):
    permission_id: int
    role_id: int


class PermissionRoleRemove(PermissionRoleCreate):
    pass


# Properties to receive via API on update
class PermissionUpdate(PermissionBase):
    pass


class PermissionInDBBase(PermissionBase):
    id: Optional[int] = None

    class Config:
        orm_mode = True


# Additional properties to return via API
class Permission(PermissionInDBBase):
    pass


# Additional properties stored in DB
class PermisisonInDB(PermissionInDBBase):
    pass
