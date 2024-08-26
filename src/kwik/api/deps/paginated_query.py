from __future__ import annotations

from typing import Annotated

import kwik.typings
from fastapi import Depends


def _parse_paginated_parameters(skip: int = 0, limit: int = 100) -> kwik.typings.ParsedPaginatedQuery:
    """
    Paginated query parameter parser, to be used as endpoint dependency
    """

    return kwik.typings.ParsedPaginatedQuery(skip=skip, limit=limit)


PaginatedQuery = Annotated[kwik.typings.ParsedPaginatedQuery, Depends(_parse_paginated_parameters)]
