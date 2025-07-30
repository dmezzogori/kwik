"""Type definitions for schema validation."""

from __future__ import annotations

from typing import TypeVar

import pydantic

from kwik.database.base import Base


class BaseModel(pydantic.BaseModel):
    """Base Pydantic model with ORM mode configuration for database integration."""

    class Config:
        orm_mode = True


ModelType = TypeVar("ModelType", bound=Base)

BaseSchemaType = TypeVar("BaseSchemaType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=pydantic.BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=pydantic.BaseModel)
