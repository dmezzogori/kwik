from __future__ import annotations

import contextlib
from typing import Type

from sqlalchemy import event
from sqlalchemy.orm import Query

from kwik import logger
from kwik.typings import ModelType, ParsedSortingQuery


def sort_query(*, model: Type[ModelType], query: Query, sort: ParsedSortingQuery) -> Query:
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
    queries = []
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        logger.error(statement)
        queries.append(statement)

    event.listen(conn, "before_cursor_execute", before_cursor_execute)
    try:
        yield queries
    finally:
        event.remove(conn, "before_cursor_execute", before_cursor_execute)
        logger.error(f"Queries: {len(queries)}")
