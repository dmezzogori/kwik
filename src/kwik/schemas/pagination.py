"""Schemas for paginated API responses."""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import pydantic
from pydantic.generics import GenericModel


class Paginated[T: pydantic.BaseModel](GenericModel):
    """Generic pagination container for API responses with total count and data."""

    total: int
    data: Sequence[T]
