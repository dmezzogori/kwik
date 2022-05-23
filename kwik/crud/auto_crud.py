from typing import Any, TypeVar

from fastapi.encoders import jsonable_encoder
from kwik import settings
from kwik.database.base import Base
from kwik.database.session import KwikSession
from kwik.exceptions import DuplicatedEntity, NotFound
from kwik.middlewares import get_request_id
from kwik.models import User
from kwik.schemas import LogCreateSchema
from kwik.typings import ParsedSortingQuery, PaginatedCRUDResult
from kwik.utils import sort_query
from pydantic import BaseModel

from . import crud_logs
from .base import CRUDCreateBase, CRUDReadBase, CRUDUpdateBase, CRUDDeleteBase

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class AutoCRUDRead(CRUDReadBase):
    # noinspection PyShadowingBuiltins
    def get(self, *, db: KwikSession, id: int) -> ModelType | None:
        return db.query(self.model).get(id)

    def get_multi(
        self,
        *,
        db: KwikSession,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters: dict[str, str],
    ) -> PaginatedCRUDResult:
        q = db.query(self.model)
        if filters:
            q = q.filter_by(**filters)

        count: int = q.count()

        if sort is not None:
            q = sort_query(model=self.model, query=q, sort=sort)

        return count, q.offset(skip).limit(limit).all()

    # noinspection PyShadowingBuiltins
    def get_if_exist(self, *, db: KwikSession, id: int) -> ModelType | None:
        r = self.get(db=db, id=id)
        if r is None:
            raise NotFound(detail=f"Entity [{self.model.__tablename__}] with id={id} does not exist")
        return r


class AutoCRUDCreate(CRUDCreateBase):
    def create(self, *, db: KwikSession, obj_in: CreateSchemaType, user: User | None = None, **kwargs) -> ModelType:
        obj_in_data = dict(obj_in)
        if user is not None:
            obj_in_data["creator_user_id"] = user.id

        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(), entity=db_obj.__tablename__, before=None, after=jsonable_encoder(db_obj),
            )
            crud_logs.logs.create(db=db, obj_in=log_in)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        db: KwikSession,
        obj_in: CreateSchemaType,
        filters: dict[str, str],
        user: User | None = None,
        raise_on_error: bool = False,
        **kwargs: Any,
    ) -> ModelType:
        obj_db: ModelType | None = db.query(self.model).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db: ModelType = self.create(db=db, obj_in=obj_in, user=user, **kwargs)
        elif raise_on_error:
            raise DuplicatedEntity
        return obj_db


class AutoCRUDUpdate(CRUDUpdateBase):
    def update(
        self, *, db: KwikSession, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any], user: User | None = None
    ) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        if user is not None:
            update_data["last_modifier_user_id"] = user.id

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(), entity=db_obj.__tablename__, before={}, after=jsonable_encoder(db_obj),
            )
            crud_logs.logs.create(db=db, obj_in=log_in)

        return db_obj


class AutoCRUDDelete(CRUDDeleteBase):
    # noinspection PyShadowingBuiltins
    def delete(self, *, db: KwikSession, id: int, user: User | None = None) -> ModelType:
        obj: ModelType = db.query(self.model).get(id)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(), entity=obj.__tablename__, before=jsonable_encoder(obj), after=None,
            )
            crud_logs.logs.create(db=db, obj_in=log_in)

        db.delete(obj)
        db.flush()
        return obj


class AutoCRUD(AutoCRUDCreate, AutoCRUDRead, AutoCRUDUpdate, AutoCRUDDelete):
    pass
