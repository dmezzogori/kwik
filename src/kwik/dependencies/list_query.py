"""Unified list query dependency combining pagination, sorting, and filters."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends

from .filter_query import FilterQuery  # noqa: TC001
from .pagination import Pagination  # noqa: TC001
from .sorting_query import SortingQuery  # noqa: TC001


def _list_query(
    pagination: Pagination,
    sort: SortingQuery,
    filters: FilterQuery,
) -> dict[str, Any]:
    """Compose pagination, sorting, and filters into a single dict."""
    return {**pagination, "sort": sort, **filters}


ListQuery = Annotated[dict[str, Any], Depends(_list_query)]

__all__ = ["ListQuery"]
