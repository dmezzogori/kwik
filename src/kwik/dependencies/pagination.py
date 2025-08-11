"""Pagination query dependency for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated, TypedDict

from fastapi import Depends


class _PaginationParameters(TypedDict):
    """Type definition for parsed pagination query parameters."""

    skip: int
    limit: int


def _parse_pagination_parameters(skip: int = 0, limit: int = 100) -> _PaginationParameters:
    """Paginated query parameter parser, to be used as endpoint dependency."""
    return _PaginationParameters(skip=skip, limit=limit)


Pagination = Annotated[_PaginationParameters, Depends(_parse_pagination_parameters)]

__all__ = ["Pagination"]
