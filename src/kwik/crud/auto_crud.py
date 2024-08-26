from __future__ import annotations

from typing import Any, NoReturn

from fastapi.encoders import jsonable_encoder
from kwik import settings
from kwik.database.session import _to_be_audited
from kwik.exceptions import DuplicatedEntity, NotFound
from kwik.middlewares import get_request_id
from kwik.schemas import LogCreateSchema
from kwik.typings import (
    CreateSchemaType,
    ModelType,
    PaginatedCRUDResult,
    ParsedSortingQuery,
    UpdateSchemaType,
)
from kwik.utils import sort_query

from .base import CRUDCreateBase, CRUDDeleteBase, CRUDReadBase, CRUDUpdateBase
from .logs import logs


class AutoCRUDRead(CRUDReadBase[ModelType]):
    # noinspection PyShadowingBuiltins
    def get(self, *, id: int) -> ModelType | None:
        return self.db.query(self.model).get(id)

    def get_all(self) -> list[ModelType]:
        return self.db.query(self.model).all()

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters: Any,
    ) -> PaginatedCRUDResult[ModelType]:
        q = self.db.query(self.model)
        if filters:
            q = q.filter_by(**filters)

        count: int = q.count()

        if sort is not None:
            q = sort_query(model=self.model, query=q, sort=sort)

        r = q.offset(skip).limit(limit).all()
        return count, r

    # noinspection PyShadowingBuiltins
    def get_if_exist(self, *, id: int) -> ModelType | NoReturn:
        r = self.get(id=id)
        if r is None:
            raise NotFound(detail=f"Entity [{self.model.__tablename__}] with id={id} does not exist")
        return r


class AutoCRUDCreate(CRUDCreateBase[ModelType, CreateSchemaType]):
    def create(self, *, obj_in: CreateSchemaType, **kwargs: Any) -> ModelType:
        obj_in_data = dict(obj_in)

        if self.user is not None and _to_be_audited(self.model):
            obj_in_data["creator_user_id"] = self.user.id

        db_obj = self.model(**obj_in_data)

        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=db_obj.__tablename__,
                before=None,
                after=jsonable_encoder(db_obj),
            )
            logs.create(obj_in=log_in)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        obj_in: CreateSchemaType,
        filters: dict[str, str],
        raise_on_error: bool = False,
        **kwargs: Any,
    ) -> ModelType:
        obj_db: ModelType | None = self.db.query(self.model).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db: ModelType = self.create(obj_in=obj_in, **kwargs)
        elif raise_on_error:
            raise DuplicatedEntity
        return obj_db


class AutoCRUDUpdate(CRUDUpdateBase[ModelType, UpdateSchemaType]):
    def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        if self.user is not None and _to_be_audited(self.model):
            update_data["last_modifier_user_id"] = self.user.id

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=db_obj.__tablename__,
                before={},
                after=jsonable_encoder(db_obj),
            )
            logs.create(obj_in=log_in)

        return db_obj


class AutoCRUDDelete(CRUDDeleteBase[ModelType]):
    def delete(self, *, id: int) -> ModelType:
        obj: ModelType = self.db.query(self.model).get(id)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=obj.__tablename__,
                before=jsonable_encoder(obj),
                after=None,
            )
            logs.create(obj_in=log_in)

        self.db.delete(obj)
        self.db.flush()
        return obj


class AutoCRUD(
    AutoCRUDCreate[ModelType, CreateSchemaType],
    AutoCRUDRead[ModelType],
    AutoCRUDUpdate[ModelType, UpdateSchemaType],
    AutoCRUDDelete[ModelType],
):
    pass
