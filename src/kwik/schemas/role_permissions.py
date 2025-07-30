"""Pydantic schemas for role permissions validation."""

from pydantic import BaseModel

from kwik.schemas.mixins import RecordInfoMixin


class _BaseSchema(BaseModel):
    role_id: int
    permission_id: int


class RolePermissionORMSchema(_BaseSchema, RecordInfoMixin):
    """ORM schema for role-permission associations with record tracking."""

    pass


class RolePermissionCreate(_BaseSchema):
    """Schema for creating role-permission associations."""

    pass
