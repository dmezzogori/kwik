"""Pydantic schemas for orm and record info validation."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


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


class AtLeastOneFieldMixin(BaseModel):
    """Mixin that ensures at least one field is provided for update operations."""

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        """Ensure at least one field is provided for update."""
        provided_fields = [k for k, val in self.model_dump().items() if val is not None]
        if not provided_fields:
            msg = "At least one field must be provided for update"
            raise ValueError(msg)
        return self
