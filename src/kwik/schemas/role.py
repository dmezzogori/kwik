from pydantic import BaseModel


class RoleBase(BaseModel):
    name: str | None = None
    is_active: bool | None = True


class RoleCreate(RoleBase):
    name: str
    is_active: bool
    is_locked: bool


class UserRoleCreate(BaseModel):
    user_id: int
    role_id: int


class UserRoleRemove(UserRoleCreate):
    pass


class RoleUpdate(RoleBase):
    is_active: bool


class RoleInDBBase(RoleBase):
    id: int | None = None

    class Config:
        orm_mode = True


class Role(RoleInDBBase):
    pass


class RoleInDB(RoleInDBBase):
    pass


class RoleLookupSchema(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True
