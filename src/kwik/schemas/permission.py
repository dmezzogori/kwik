from __future__ import annotations

from pydantic import BaseModel

from kwik.schemas.mixins.orm import ORMMixin


class _BaseSchema(BaseModel):
    name: str


class PermissionORMSchema(ORMMixin, _BaseSchema):
    """ORM schema for permissions with database ID."""

    pass


class PermissionCreate(_BaseSchema):
    """Schema for creating new permissions."""

    pass


class PermissionUpdate(_BaseSchema):
    """Schema for updating existing permissions."""

    pass
