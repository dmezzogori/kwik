"""Schemas for paginated API responses."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic

from pydantic.generics import GenericModel

from ._base import BaseSchemaType


class Paginated(GenericModel, Generic[BaseSchemaType]):
    """Generic pagination container for API responses with total count and data."""

    total: int
    data: Sequence[BaseSchemaType]
