from __future__ import annotations

from typing import Generic, TypeVar

from pydantic.generics import GenericModel

# Use TypeVar to avoid circular import
T = TypeVar("T")


class Paginated(GenericModel, Generic[T]):
    total: int
    data: list[T]
