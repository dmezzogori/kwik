"""Pydantic schemas for role validation."""

from pydantic import BaseModel


class RoleBase(BaseModel):
    """Base schema for role data with common fields."""

    name: str | None = None
    is_active: bool | None = True


class RoleCreate(RoleBase):
    """Schema for creating new roles."""

    name: str
    is_active: bool
    is_locked: bool


class UserRoleCreate(BaseModel):
    """Schema for creating user-role associations."""

    user_id: int
    role_id: int


class UserRoleRemove(UserRoleCreate):
    """Schema for removing user-role associations."""


class RoleUpdate(RoleBase):
    """Schema for updating existing roles."""

    name: str | None = None
    is_active: bool | None = None


class RoleInDBBase(RoleBase):
    """Base schema for roles stored in database with ID."""

    id: int | None = None

    class Config:
        """Pydantic configuration for ORM compatibility."""

        orm_mode = True


class Role(RoleInDBBase):
    """Role schema for API responses."""


class RoleInDB(RoleInDBBase):
    """Role schema for internal database operations."""


class RoleLookupSchema(BaseModel):
    """Schema for role lookup operations with ID and name."""

    id: int
    name: str

    class Config:
        """Pydantic configuration for ORM compatibility."""

        orm_mode = True
