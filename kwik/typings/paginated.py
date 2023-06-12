from __future__ import annotations

from typing import Generic, TypedDict

from .schemas import ModelType


class ParsedPaginatedQuery(TypedDict):
    skip: int
    limit: int


class PaginatedResponse(TypedDict, Generic[ModelType]):
    data: list[ModelType]
    total: int


PaginatedCRUDResult = tuple[int, list[ModelType]]
