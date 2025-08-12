"""Pydantic schemas for permission validation."""

from __future__ import annotations

from pydantic import BaseModel

from .mixins import ORMMixin


class _BaseSchema(BaseModel):
    name: str


class PermissionProfile(ORMMixin, _BaseSchema):
    """Schema for permission profile information."""


class PermissionDefinition(_BaseSchema):
    """Schema for defining new permissions."""


class PermissionUpdate(_BaseSchema):
    """Schema for updating existing permissions."""
