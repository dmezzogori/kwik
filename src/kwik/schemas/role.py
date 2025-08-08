"""Pydantic schemas for role validation."""

from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    """Base schema for role data with common fields."""

    name: str | None = None
    is_active: bool | None = True


class RoleDefinition(BaseModel):
    """Schema for defining new roles."""

    name: str
    is_active: bool


class RoleUpdate(RoleBase):
    """Schema for updating existing roles."""

    name: str | None = None
    is_active: bool | None = None


class RoleInDBBase(RoleBase):
    """Base schema for roles stored in database with ID."""

    id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleProfile(RoleInDBBase):
    """Schema for role profile information."""


class RoleInDB(RoleInDBBase):
    """Role schema for internal database operations."""


class RoleLookup(BaseModel):
    """Schema for role lookup operations with ID and name."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class RolePermissionAssignment(BaseModel):
    """Schema for assigning permissions to roles."""

    permission_id: int
