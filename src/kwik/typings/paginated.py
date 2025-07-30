"""Type definitions for paginated responses."""

from __future__ import annotations

from typing import Generic, TypedDict

from .schemas import ModelType


class ParsedPaginatedQuery(TypedDict):
    """Type definition for parsed pagination query parameters."""

    skip: int
    limit: int


class PaginatedResponse(TypedDict, Generic[ModelType]):
    """Type definition for paginated API responses with data and total count."""

    data: list[ModelType]
    total: int


PaginatedCRUDResult = tuple[int, list[ModelType]]
