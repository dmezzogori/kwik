"""Pydantic schemas for role validation."""

from typing import Annotated

from pydantic import BaseModel
from pydantic.types import StringConstraints

from .mixins import AtLeastOneFieldMixin, ORMMixin

_RoleName = Annotated[
    str,
    StringConstraints(
        min_length=1,
        strip_whitespace=True,
        to_lower=True,
    ),
]


class RoleDefinition(BaseModel):
    """Schema for defining new roles."""

    name: _RoleName
    is_active: bool


class RoleUpdate(AtLeastOneFieldMixin):
    """Schema for updating existing roles."""

    name: _RoleName | None = None
    is_active: bool | None = None


class RoleProfile(ORMMixin):
    """Schema for role profile information."""

    name: _RoleName
    is_active: bool


class RolePermissionAssignment(BaseModel):
    """Schema for assigning permissions to roles."""

    permission_id: int


class RoleUserAssignment(BaseModel):
    """Schema for assigning users to roles."""

    user_id: int
