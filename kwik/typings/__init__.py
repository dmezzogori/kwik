from typing import Any, Optional, TypeVar

import pydantic

from kwik.database.base import Base


class BaseModel(pydantic.BaseModel):
    class Config:
        orm_mode = True


ModelType = TypeVar("ModelType", bound=Base)

BaseSchemaType = TypeVar("BaseSchemaType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=pydantic.BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=pydantic.BaseModel)


SortingQuery = str
ParsedSortingQuery = list[tuple[str, str]] | None
FilterQuery = dict[str, Any]
PaginatedQuery = dict[str, int]


PaginatedCRUDResult = tuple[int, list[ModelType]]
