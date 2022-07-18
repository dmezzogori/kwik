from typing import Any, NoReturn

from fastapi.encoders import jsonable_encoder
from kwik import settings
from kwik.database.session import KwikSession, _to_be_audited
from kwik.exceptions import DuplicatedEntity, NotFound
from kwik.middlewares import get_request_id
from kwik.models import User
from kwik.schemas import LogCreateSchema
from kwik.typings import ModelType, CreateSchemaType, UpdateSchemaType
from kwik.typings import ParsedSortingQuery, PaginatedCRUDResult
from kwik.utils import sort_query

from .base import CRUDCreateBase, CRUDReadBase, CRUDUpdateBase, CRUDDeleteBase
from .logs import logs


class AutoCRUDRead(CRUDReadBase[ModelType]):
    # noinspection PyShadowingBuiltins
    def get(self, *, db: KwikSession | None = None, id: int) -> ModelType | None:
        _db = db if db is not None else self.db
        return _db.query(self.model).get(id)

    def get_all(self, *, db: KwikSession | None = None) -> list[ModelType]:
        _db = db if db is not None else self.db
        return _db.query(self.model).all()

    def get_multi(
        self,
        *,
        db: KwikSession | None = None,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters: Any,
    ) -> PaginatedCRUDResult[ModelType]:
        _db = db if db is not None else self.db
        q = _db.query(self.model)
        if filters:
            q = q.filter_by(**filters)

        count: int = q.count()

        if sort is not None:
            q = sort_query(model=self.model, query=q, sort=sort)

        r = q.offset(skip).limit(limit).all()
        return count, r

    # noinspection PyShadowingBuiltins
    def get_if_exist(self, *, db: KwikSession | None = None, id: int) -> ModelType | NoReturn:
        _db = db if db is not None else self.db
        r = self.get(db=_db, id=id)
        if r is None:
            raise NotFound(detail=f"Entity [{self.model.__tablename__}] with id={id} does not exist")
        return r


class AutoCRUDCreate(CRUDCreateBase[ModelType, CreateSchemaType]):
    def create(
        self, *, db: KwikSession | None = None, obj_in: CreateSchemaType, user: User | None = None, **kwargs
    ) -> ModelType:
        obj_in_data = dict(obj_in)

        _user = user if user is not None else self.user

        if _user is not None and _to_be_audited(self.model):
            obj_in_data["creator_user_id"] = _user.id

        db_obj = self.model(**obj_in_data)

        _db = db if db is not None else self.db
        _db.add(db_obj)
        _db.flush()
        _db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=db_obj.__tablename__,
                before=None,
                after=jsonable_encoder(db_obj),
            )
            logs.create(db=_db, obj_in=log_in)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        db: KwikSession | None = None,
        obj_in: CreateSchemaType,
        filters: dict[str, str],
        user: User | None = None,
        raise_on_error: bool = False,
        **kwargs: Any,
    ) -> ModelType:

        _db = db if db is not None else self.db
        _user = user if user is not None else self.user

        obj_db: ModelType | None = _db.query(self.model).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db: ModelType = self.create(db=_db, obj_in=obj_in, user=_user, **kwargs)
        elif raise_on_error:
            raise DuplicatedEntity
        return obj_db


class AutoCRUDUpdate(CRUDUpdateBase[ModelType, UpdateSchemaType]):
    def update(
        self,
        *,
        db: KwikSession | None = None,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        user: User | None = None,
    ) -> ModelType:

        _db = db if db is not None else self.db
        _user = user if user is not None else self.user

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        if _user is not None and _to_be_audited(self.model):
            update_data["last_modifier_user_id"] = _user.id

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        _db.add(db_obj)
        _db.flush()
        _db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=db_obj.__tablename__,
                before={},
                after=jsonable_encoder(db_obj),
            )
            logs.create(db=_db, obj_in=log_in)

        return db_obj


class AutoCRUDDelete(CRUDDeleteBase[ModelType]):
    # noinspection PyShadowingBuiltins
    def delete(self, *, db: KwikSession | None = None, id: int, user: User | None = None) -> ModelType:
        _db = db if db is not None else self.db
        obj: ModelType = _db.query(self.model).get(id)

        if settings.DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=obj.__tablename__,
                before=jsonable_encoder(obj),
                after=None,
            )
            logs.create(db=_db, obj_in=log_in)

        _db.delete(obj)
        _db.flush()
        return obj


class AutoCRUD(
    AutoCRUDCreate[ModelType, CreateSchemaType],
    AutoCRUDRead[ModelType],
    AutoCRUDUpdate[ModelType, UpdateSchemaType],
    AutoCRUDDelete[ModelType],
):
    pass
