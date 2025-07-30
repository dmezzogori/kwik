import typing
from datetime import datetime

from pydantic import BaseModel, create_model
from sqlalchemy import inspect as ins
from sqlalchemy.sql.sqltypes import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
)

from kwik import typings

TYPE_MAPPINGS = {
    Integer: int,
    BigInteger: int,
    String: str,
    DateTime: datetime,
    Float: float,
    JSON: dict,
    Boolean: bool,
}


def get_column_fields(cls):
    """Extract column metadata from SQLAlchemy model for schema generation."""
    i = ins(cls)
    for column in i.columns:
        colname = column.key
        type_ = TYPE_MAPPINGS[type(column.type)]
        default = column.default.arg if column.default else None
        nullable = column.nullable
        yield colname, type_, default, nullable


def synth_schemas(cls):
    """Generate Pydantic schemas from SQLAlchemy model automatically."""
    kw = {}
    for col_name, type_, default, nullable in get_column_fields(cls):
        if col_name not in ("creation_time", "creator_user_id"):
            if default is not None and not callable(default):
                kw[col_name] = default
            elif nullable:
                kw[col_name] = typing.Optional[type_], None
            else:
                kw[col_name] = type_, ...

    bkw = dict(kw)
    BaseSchema: BaseModel = create_model(
        f"{cls.__name__}Base", __base__=typings.BaseModel, **bkw,
    )
    CreateModel: BaseModel = create_model(
        f"{cls.__name__}Create", **{k: v for k, v in kw.items() if k != "id"},
    )
    UpdateModel: BaseModel = create_model(
        f"{cls.__name__}Update", **{k: v for k, v in kw.items() if k != "id"},
    )
    return BaseSchema, CreateModel, UpdateModel
