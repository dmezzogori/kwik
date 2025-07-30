"""Database query utility functions."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from sqlalchemy import event

from kwik import logger

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


@contextlib.contextmanager
def count_queries(conn):
    """Context manager to count and log SQL queries executed."""
    queries = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
        logger.error(statement)
        queries.append(statement)

    event.listen(conn, "before_cursor_execute", before_cursor_execute)
    try:
        yield queries
    finally:
        event.remove(conn, "before_cursor_execute", before_cursor_execute)
        logger.error(f"Queries: {len(queries)}")
