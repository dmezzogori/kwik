"""Database query utility functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Query

    from kwik.typings import ModelType, ParsedSortingQuery
else:
    from typing import TypeVar

    ModelType = TypeVar("ModelType")
    ParsedSortingQuery = TypeVar("ParsedSortingQuery")


def sort_query(*, model: type[ModelType], query: Query, sort: ParsedSortingQuery) -> Query:
    """Apply sorting parameters to SQLAlchemy query."""
    order_by = []
    for attr, order in sort:
        model_attr = getattr(model, attr)
        if order == "asc":
            order_by.append(model_attr.asc())
        else:
            order_by.append(model_attr.desc())
    return query.order_by(*order_by)
