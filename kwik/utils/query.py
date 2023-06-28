from __future__ import annotations

from typing import Type

from kwik.typings import ModelType, ParsedSortingQuery
from sqlalchemy.orm import Query


def sort_query(*, model: Type[ModelType], query: Query, sort: ParsedSortingQuery) -> Query:
    order_by = []
    for attr, order in sort:
        model_attr = getattr(model, attr)
        if order == "asc":
            order_by.append(model_attr.asc())
        else:
            order_by.append(model_attr.desc())
    return query.order_by(*order_by)
