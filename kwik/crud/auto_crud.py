from typing import Any, TypeVar

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from kwik import settings
from kwik.database.base import Base
from kwik.database.session import KwikSession
from kwik.exceptions import DuplicatedEntity
from kwik.middlewares import get_request_id
from kwik.models import User
from kwik.schemas import LogCreateSchema
from kwik.typings import ParsedSortingQuery, PaginatedCRUDResult
from kwik.utils import sort_query
from . import crud_logs

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


from .base import CRUDCreateBase, CRUDReadBase, CRUDUpdateBase, CRUDDeleteBase


class AutoCRUDRead(CRUDReadBase):
    def get(self, *, db: KwikSession, id: int) -> ModelType | None:
        return db.query(self.model).get(id)

    def get_multi(
        self,
        *,
        db: KwikSession,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters: dict[str, str]
    ) -> PaginatedCRUDResult:
        q = db.query(self.model)
        if filters:
            q = q.filter_by(**filters)

        count: int = q.count()

        if sort is not None:
            q = sort_query(model=self.model, query=q, sort=sort)

        return count, q.offset(skip).limit(limit).all()


class AutoCRUDCreate(CRUDCreateBase):
    def create(self, *, db: KwikSession, obj_in: CreateSchemaType, user: User | None = None) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        if user is not None:
            db_obj: ModelType = self.model(**obj_in_data, creator_user_id=user.id)
        else:
            db_obj: ModelType = self.model(**obj_in_data)
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
        user: User | None = None,
        raise_on_error: bool = False,
        **kwargs: dict[str, str]
    ) -> ModelType:
        obj_db: ModelType | None = db.query(self.model).filter_by(**kwargs).one_or_none()
        if obj_db is None:
            obj_db: ModelType = self.create(db=db, obj_in=obj_in, user=user)
        elif raise_on_error:
            raise DuplicatedEntity()
        return obj_db


class AutoCRUDUpdate(CRUDUpdateBase):
    def update(
        self, *, db: KwikSession, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any], user: User | None = None
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        if user is not None:
            update_data["last_modifier_user_id"] = user.id

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=db_obj.__tablename__,
                before=obj_data,
                after=jsonable_encoder(db_obj),
            )
            crud_logs.logs.create(db=db, obj_in=log_in)

        return db_obj


class AutoCRUDDelete(CRUDDeleteBase):
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
