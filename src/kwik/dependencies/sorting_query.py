"""Sorting query dependency for FastAPI endpoints."""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Depends

ParsedSortingQuery = list[tuple[str, str]]


def _parse_sorting_query(sorting: str | None = None) -> ParsedSortingQuery:
    """
    Sorting query parameter parser, to be used as endpoint dependency.

    The sorting parameter is a comma-separated list of fields to sort by.
    Each field can be postfixed with a colon and a direction ("asc" or "desc").
    If no direction is specified, "asc" is assumed.

    Example:
    >>> _parse_sorting_query("id:desc,created_at")
    [("id", "desc"), ("created_at", "asc")]

    """
    sort = []
    if sorting is not None:
        pattern = r"(\w+)(?::(asc|desc))?"
        for field, direction in re.findall(pattern, sorting):
            sort.append((field, direction or "asc"))
    return sort


Sorting = Annotated[ParsedSortingQuery, Depends(_parse_sorting_query)]

__all__ = ["Sorting"]
