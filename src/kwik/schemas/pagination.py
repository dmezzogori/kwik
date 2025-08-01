"""Schemas for paginated API responses."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

import pydantic
from pydantic.generics import GenericModel

# TypeVar for any Pydantic model used in paginated responses
T = TypeVar("T", bound=pydantic.BaseModel)


class Paginated(GenericModel, Generic[T]):
    """Generic pagination container for API responses with total count and data."""

    total: int
    data: Sequence[T]
