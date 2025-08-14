"""Pydantic schemas for role validation."""

from pydantic import BaseModel

from .mixins import ORMMixin


class RoleDefinition(BaseModel):
    """Schema for defining new roles."""

    name: str
    is_active: bool


class RoleUpdate(BaseModel):
    """Schema for updating existing roles."""

    name: str | None = None
    is_active: bool | None = None


class RoleProfile(ORMMixin):
    """Schema for role profile information."""

    name: str
    is_active: bool


class RolePermissionAssignment(BaseModel):
    """Schema for assigning permissions to roles."""

    permission_id: int


class RoleUserAssignment(BaseModel):
    """Schema for assigning users to roles."""

    user_id: int
