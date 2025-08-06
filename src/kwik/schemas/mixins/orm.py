"""Pydantic schemas for orm validation."""

from pydantic import BaseModel, ConfigDict


class ORMMixin(BaseModel):
    """Mixin providing ORM mode configuration and ID field for database schemas."""

    id: int

    model_config = ConfigDict(from_attributes=True)
