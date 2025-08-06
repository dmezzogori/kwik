"""Schemas for paginated API responses."""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import pydantic


class Paginated[T: pydantic.BaseModel](pydantic.BaseModel):
    """Generic pagination container for API responses with total count and data."""

    total: int
    data: Sequence[T]
