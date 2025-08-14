"""Pydantic schemas for permission validation."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel
from pydantic.types import StringConstraints

from .mixins import ORMMixin

_PermissionName = Annotated[
    str,
    StringConstraints(
        min_length=1,
        strip_whitespace=True,
        to_lower=True,
    ),
]


class _BaseSchema(BaseModel):
    name: _PermissionName


class PermissionProfile(ORMMixin, _BaseSchema):
    """Schema for permission profile information."""


class PermissionDefinition(_BaseSchema):
    """Schema for defining new permissions."""


class PermissionUpdate(_BaseSchema):
    """Schema for updating existing permissions."""
