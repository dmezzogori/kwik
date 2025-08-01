"""Type definitions for paginated responses."""

from __future__ import annotations

from typing import Generic, TypedDict, TypeVar

T = TypeVar("T")


class ParsedPaginatedQuery(TypedDict):
    """Type definition for parsed pagination query parameters."""

    skip: int
    limit: int


class PaginatedResponse(TypedDict, Generic[T]):
    """Type definition for paginated API responses with data and total count."""

    data: list[T]
    total: int


PaginatedCRUDResult = tuple[int, list[T]]
