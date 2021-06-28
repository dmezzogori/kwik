import typing
from datetime import datetime

from pydantic import create_model, BaseModel
from sqlalchemy import inspect as ins
from sqlalchemy.sql.sqltypes import Integer, BigInteger, String, DateTime, Float, JSON


TYPE_MAPPINGS = {
    Integer: int,
    BigInteger: int,
    String: str,
    DateTime: datetime,
    Float: float,
    JSON: typing.Dict
}


def get_column_fields(cls):
    i = ins(cls)
    for column in i.columns:
        colname = column.key
        type_ = TYPE_MAPPINGS[type(column.type)]
        default = column.default.arg if column.default else None
        nullable = column.nullable
        yield colname, type_, default, nullable


class MyBaseModel(BaseModel):
    class Config:
        orm_mode = True


def synth_schemas(cls):

    kw = {}
    for col_name, type_, default, nullable in get_column_fields(cls):
        # TODO: trovare giro più carino
        if col_name == 'creation_time':
            kw[col_name] = type_, ...

        elif default is not None and not callable(default):
            kw[col_name] = default
        elif nullable:
            kw[col_name] = typing.Optional[type_], None
        else:
            kw[col_name] = type_, ...

    bkw = dict(kw)
    BaseSchema: BaseModel = create_model(f'{cls.__name__}Base', __base__=MyBaseModel, **bkw)
    CreateModel: BaseModel = create_model(f'{cls.__name__}Create', **{k: v for k, v in kw.items() if k != 'id'})
    UpdateModel: BaseModel = create_model(f'{cls.__name__}Update', **{k: v for k, v in kw.items() if k != 'id'})
    return BaseSchema, CreateModel, UpdateModel
