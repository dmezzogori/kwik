"""Pagination query dependency for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

import kwik.typings


def _parse_paginated_parameters(skip: int = 0, limit: int = 100) -> kwik.typings.ParsedPaginatedQuery:
    """Paginated query parameter parser, to be used as endpoint dependency."""
    return kwik.typings.ParsedPaginatedQuery(skip=skip, limit=limit)


PaginatedQuery = Annotated[kwik.typings.ParsedPaginatedQuery, Depends(_parse_paginated_parameters)]
