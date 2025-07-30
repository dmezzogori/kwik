"""Base CRUD classes and operations for database models."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Generic, get_args

from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.database.session import KwikSession
    from kwik.typings import (
        CreateSchemaType,
        ModelType,
        PaginatedCRUDResult,
        ParsedSortingQuery,
        UpdateSchemaType,
    )

    T = Generic[ModelType, CreateSchemaType, UpdateSchemaType]
else:
    from typing import TypeVar

    ModelType = TypeVar("ModelType")
    CreateSchemaType = TypeVar("CreateSchemaType")
    UpdateSchemaType = TypeVar("UpdateSchemaType")
    T = Generic[ModelType, CreateSchemaType, UpdateSchemaType]


class DBSession:
    """Descriptor for accessing database session from context variables."""

    def __get__(self, obj, objtype=None) -> Session:
        """Get the database session from context variables."""
        if (db := db_conn_ctx_var.get()) is not None:
            return db
        msg = "No database connection available"
        raise Exception(msg)


class CurrentUser:
    """Descriptor for accessing current user from context variables."""

    def __get__(self, obj, objtype=None):
        """Get the current user from context variables."""
        return current_user_ctx_var.get()


class CRUDBase(abc.ABC, Generic[ModelType]):
    """Base class for all CRUD operations with model type safety and context access."""

    db: KwikSession = DBSession()
    user = CurrentUser()
    model: type[ModelType]

    _instances: dict[str, T] = {}

    def __init__(self, model: type[ModelType] | None = None) -> None:
        """CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        """
        _model = model if model is not None else get_args(self.__orig_bases__[0])[0]
        self.model = _model
        CRUDBase._instances[_model] = self

    @classmethod
    def get_instance(cls: T, model: type[ModelType]) -> T:
        """Get existing CRUD instance for the given model."""
        return CRUDBase._instances[model]


class CRUDReadBase(CRUDBase[ModelType]):
    """Abstract base class defining read operation interface for CRUD implementations."""

    @abc.abstractmethod
    def get(self, *, id: int) -> ModelType | None:
        """Get single record by primary key ID."""

    @abc.abstractmethod
    def get_all(self) -> list[ModelType]:
        """Get all records from the table."""

    @abc.abstractmethod
    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters,
    ) -> PaginatedCRUDResult[ModelType]:
        """Get multiple records with pagination, filtering, and sorting."""

    @abc.abstractmethod
    def get_if_exist(self, *, id: int) -> ModelType:
        """Get record by ID or raise exception if it doesn't exist."""


class CRUDCreateBase(CRUDBase, Generic[ModelType, CreateSchemaType]):
    """Abstract base class defining create operation interface for CRUD implementations."""

    @abc.abstractmethod
    def create(
        self,
        *,
        obj_in: CreateSchemaType,
    ) -> ModelType:
        """Create new record from schema data."""

    @abc.abstractmethod
    def create_if_not_exist(
        self,
        *,
        obj_in: CreateSchemaType,
        filters: dict[str, str],
        raise_on_error: bool = False,
    ) -> ModelType:
        """Create record if it doesn't exist, or return existing record."""


class CRUDUpdateBase(CRUDBase, Generic[ModelType, UpdateSchemaType]):
    """Abstract base class defining update operation interface for CRUD implementations."""

    @abc.abstractmethod
    def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update existing record with new data."""


class CRUDDeleteBase(CRUDBase[ModelType]):
    """Abstract base class defining delete operation interface for CRUD implementations."""

    @abc.abstractmethod
    def delete(self, *, id: int) -> ModelType:
        """Delete record by ID and return the deleted object."""
