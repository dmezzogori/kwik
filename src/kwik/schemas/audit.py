"""Pydantic schemas for audit validation."""

from pydantic import BaseModel

from kwik.schemas.mixins.orm import ORMMixin


class _BaseSchema(BaseModel):
    client_host: str
    request_id: str | None = None
    user_id: int | None = None
    impersonator_user_id: int | None = None
    method: str
    headers: str
    url: str
    query_params: str | None = None
    path_params: str | None = None
    body: str | None = None
    process_time: float | None = None
    status_code: int | None = None


class AuditProfile(ORMMixin, _BaseSchema):
    """Schema for audit profile information with database ID."""


class AuditEntry(_BaseSchema):
    """Schema for creating new audit log entries."""
