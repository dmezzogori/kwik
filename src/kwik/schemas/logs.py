"""Pydantic schemas for logs validation."""

from typing import Any

from pydantic import BaseModel

from kwik.schemas.mixins.orm import ORMMixin


class _BaseSchema(BaseModel):
    request_id: str | None = None
    entity: str | None = None
    before: Any | None = None
    after: Any | None = None


class LogORMSchema(ORMMixin, _BaseSchema):
    """ORM schema for application log entries with database ID."""



class LogCreateSchema(_BaseSchema):
    """Schema for creating new application log entries."""

