from sqlalchemy.orm import Query

from kwik.typings import ModelType, ParsedSortingQuery


def sort_query(*, model: ModelType, query: Query, sort: ParsedSortingQuery) -> Query:
    order_by = []
    for attr, order in sort:
        model_attr = getattr(model, attr)
        if order == "asc":
            order_by.append(model_attr.asc())
        else:
            order_by.append(model_attr.desc())
    return query.order_by(*order_by)
