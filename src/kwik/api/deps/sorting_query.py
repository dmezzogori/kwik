from __future__ import annotations

import re
from typing import Annotated

import kwik.typings
from fastapi import Depends


def parse_sorting_query(sorting: str | None = None) -> kwik.typings.ParsedSortingQuery:
    """
    Sorting query parameter parser, to be used as endpoint dependency
    The sorting parameter is a comma-separated list of fields to sort by.
    Each field can be postfixed with a colon and a direction ("asc" or "desc").
    If no direction is specified, "asc" is assumed.

    Example:
    >>> tuple(parse_sorting_query("id:desc,created_at"))
    (("id", "desc"), ("created_at", "asc"))
    """

    if sorting is not None:
        sort = []
        pattern = r"(\w+)(?::(asc|desc))?"
        for field, direction in re.findall(pattern, sorting):
            if direction and direction not in ("asc", "desc"):
                raise ValueError(f"Invalid sorting {direction=} for {field=}")
            sort.append((field, direction or "asc"))
        return sort


SortingQuery = Annotated[kwik.typings.ParsedSortingQuery, Depends(parse_sorting_query)]
