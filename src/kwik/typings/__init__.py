"""Type definitions package for kwik framework.

This package contains type hints, schemas, and utility types for improved type safety
and better IDE support throughout the kwik web framework.
"""

from __future__ import annotations

from .filter_query import FilterQuery
from .paginated import PaginatedCRUDResult, PaginatedResponse, ParsedPaginatedQuery
from .schemas import (
    BaseModel,
    BaseSchemaType,
    CreateSchemaType,
    ModelType,
    UpdateSchemaType,
)
from .sorting_query import ParsedSortingQuery, SortingQuery
from .token import Token

__all__ = [
    "BaseModel",
    "BaseSchemaType",
    "CreateSchemaType",
    "FilterQuery",
    "ModelType",
    "PaginatedCRUDResult",
    "PaginatedResponse",
    "ParsedPaginatedQuery",
    "ParsedSortingQuery",
    "SortingQuery",
    "Token",
    "UpdateSchemaType",
]
