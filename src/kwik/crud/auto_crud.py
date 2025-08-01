"""Automatic CRUD operations base class for database models."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from fastapi.encoders import jsonable_encoder

from kwik.core.settings import get_settings
from kwik.exceptions import DuplicatedEntity, NotFound
from kwik.middlewares import get_request_id
from kwik.schemas import LogCreateSchema
from kwik.utils import sort_query

if TYPE_CHECKING:
    from kwik.typings import (
        CreateSchemaType,
        ModelType,
        PaginatedCRUDResult,
        ParsedSortingQuery,
        UpdateSchemaType,
    )
else:
    from typing import TypeVar

    ModelType = TypeVar("ModelType")
    CreateSchemaType = TypeVar("CreateSchemaType")
    UpdateSchemaType = TypeVar("UpdateSchemaType")
    PaginatedCRUDResult = TypeVar("PaginatedCRUDResult")
    ParsedSortingQuery = TypeVar("ParsedSortingQuery")

from .base import CRUDBase
from .logs import logs


class AutoCRUD(CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Complete CRUD implementation combining create, read, update, and delete operations."""

    def get(self, *, id: int) -> ModelType | None:  # noqa: A002
        """Get single record by primary key ID."""
        return self.db.query(self.model).get(id)

    def get_all(self) -> list[ModelType]:
        """Get all records from the table."""
        return self.db.query(self.model).all()

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters: Any,
    ) -> PaginatedCRUDResult[ModelType]:
        """Get multiple records with pagination, filtering, and sorting."""
        q = self.db.query(self.model)
        if filters:
            q = q.filter_by(**filters)

        count: int = q.count()

        if sort is not None:
            q = sort_query(model=self.model, query=q, sort=sort)

        r = q.offset(skip).limit(limit).all()
        return count, r

    def get_if_exist(self, *, id: int) -> ModelType:  # noqa: A002
        """Get record by ID or raise NotFound exception if it doesn't exist."""
        r = self.get(id=id)
        if r is None:
            raise NotFound(detail=f"Entity [{self.model.__tablename__}] with id={id} does not exist")
        return r

    def create(self, *, obj_in: CreateSchemaType, **kwargs) -> ModelType:
        """Create new record from schema data."""
        obj_in_data = dict(obj_in)

        # Import here to avoid circular import
        from kwik.database.mixins import RecordInfoMixin  # noqa: PLC0415

        if self.user is not None and inspect.isclass(self.model) and issubclass(self.model, RecordInfoMixin):
            obj_in_data["creator_user_id"] = self.user.id

        db_obj = self.model(**obj_in_data)

        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)

        if get_settings().DB_LOGGER:
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
        """Create record if it doesn't exist, or return existing record."""
        obj_db: ModelType | None = self.db.query(self.model).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db: ModelType = self.create(obj_in=obj_in, **kwargs)
        elif raise_on_error:
            raise DuplicatedEntity
        return obj_db

    def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]) -> ModelType:
        """Update existing record with new data and track changes."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)

        # Import here to avoid circular import
        from kwik.database.mixins import RecordInfoMixin  # noqa: PLC0415

        if self.user is not None and inspect.isclass(self.model) and issubclass(self.model, RecordInfoMixin):
            update_data["last_modifier_user_id"] = self.user.id

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)

        if get_settings().DB_LOGGER:
            log_in = LogCreateSchema(
                request_id=get_request_id(),
                entity=db_obj.__tablename__,
                before={},
                after=jsonable_encoder(db_obj),
            )
            logs.create(obj_in=log_in)

        return db_obj

    def delete(self, *, id: int) -> ModelType:  # noqa: A002
        """Delete record by ID and return the deleted object."""
        obj: ModelType = self.db.query(self.model).get(id)

        if get_settings().DB_LOGGER:
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
