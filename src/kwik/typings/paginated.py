"""Type definitions for paginated responses."""

from __future__ import annotations

from typing import TypedDict


class PaginatedResponse[T](TypedDict):
    """Type definition for paginated API responses with data and total count."""

    data: list[T]
    total: int
