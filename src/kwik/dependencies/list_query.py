"""Unified list query dependency combining pagination, sorting, and filters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, TypedDict

from fastapi import Depends

from .filter_query import Filters  # noqa: TC001
from .pagination import Pagination  # noqa: TC001
from .sorting_query import Sorting  # noqa: TC001

if TYPE_CHECKING:
    from .sorting_query import ParsedSortingQuery


class _ListQueryParameters(TypedDict, total=False):
    """Type definition for combined list query parameters."""

    skip: int
    limit: int
    sort: ParsedSortingQuery


def _list_query(
    pagination: Pagination,
    sort: Sorting,
    filters: Filters,
) -> _ListQueryParameters:
    """Compose pagination, sorting, and filters into a single dict."""
    return {**pagination, "sort": sort, **filters}  # type: ignore[return-value]


ListQuery = Annotated[_ListQueryParameters, Depends(_list_query)]

__all__ = ["ListQuery"]
