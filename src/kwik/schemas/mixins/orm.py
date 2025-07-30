"""Pydantic schemas for orm validation."""

from pydantic import BaseModel


class ORMMixin(BaseModel):
    """Mixin providing ORM mode configuration and ID field for database schemas."""

    id: int

    class Config:
        """Pydantic configuration for ORM compatibility."""

        orm_mode = True
