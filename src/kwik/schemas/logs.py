"""Pydantic schemas for logs validation."""

from typing import Any

from pydantic import BaseModel

from kwik.schemas.mixins.orm import ORMMixin


class _BaseSchema(BaseModel):
    request_id: str | None = None
    entity: str | None = None
    before: Any | None = None
    after: Any | None = None


class LogProfile(ORMMixin, _BaseSchema):
    """Schema for application log profile information with database ID."""


class LogEntry(_BaseSchema):
    """Schema for creating new application log entries."""
