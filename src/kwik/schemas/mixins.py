"""Pydantic schemas for orm and record info validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMMixin(BaseModel):
    """Mixin providing ORM mode configuration and ID field for database schemas."""

    id: int

    model_config = ConfigDict(from_attributes=True)


class RecordInfoMixin(ORMMixin):
    """Mixin providing record creation and modification tracking fields."""

    creation_time: datetime
    last_modification_time: datetime | None = None
    creator_user_id: int
    last_modifier_user_id: int | None = None
