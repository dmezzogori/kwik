"""Pydantic schemas for role validation."""

from pydantic import BaseModel


class RoleBase(BaseModel):
    """Base schema for role data with common fields."""

    name: str | None = None
    is_active: bool | None = True


class RoleDefinition(RoleBase):
    """Schema for defining new roles."""

    name: str
    is_active: bool
    is_locked: bool


class UserRoleAssignment(BaseModel):
    """Schema for assigning roles to users."""

    user_id: int
    role_id: int


class UserRoleRevocation(UserRoleAssignment):
    """Schema for revoking roles from users."""


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


class RoleProfile(RoleInDBBase):
    """Schema for role profile information."""


class RoleInDB(RoleInDBBase):
    """Role schema for internal database operations."""


class RoleLookup(BaseModel):
    """Schema for role lookup operations with ID and name."""

    id: int
    name: str

    class Config:
        """Pydantic configuration for ORM compatibility."""

        orm_mode = True
