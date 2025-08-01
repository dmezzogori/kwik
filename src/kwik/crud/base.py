"""Base CRUD classes and operations for database models."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Generic, get_args

from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.schemas._base import CreateSchemaType, ModelType, UpdateSchemaType
    from kwik.typings import PaginatedCRUDResult, ParsedSortingQuery
else:
    from typing import TypeVar

    ModelType = TypeVar("ModelType")
    CreateSchemaType = TypeVar("CreateSchemaType")
    UpdateSchemaType = TypeVar("UpdateSchemaType")


class NoDatabaseConnectionError(Exception):
    """Raised when no database connection is available."""


class DBSession:
    """Descriptor for accessing database session from context variables."""

    def __get__(self, obj: object, objtype: type | None = None) -> Session:
        """Get the database session from context variables."""
        if (db := db_conn_ctx_var.get()) is not None:
            return db
        msg = "No database connection available"
        raise NoDatabaseConnectionError(msg)


class CurrentUser:
    """Descriptor for accessing current user from context variables."""

    def __get__(self, obj: object, objtype: type | None = None) -> object:
        """Get the current user from context variables."""
        return current_user_ctx_var.get()


class CRUDBase(abc.ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class for all CRUD operations with model type safety and context access."""

    db = DBSession()
    user = CurrentUser()
    model: type[ModelType]

    def __init__(self) -> None:
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        The model type is automatically extracted from the generic type parameters.
        """
        # Extract model type from generic parameters
        bases = getattr(self, "__orig_bases__", None)
        if bases is not None:
            args = get_args(bases[0])
            if args:
                self.model = args[0]
            else:
                msg = "Model type must be specified via generic type parameters: CRUDBase[Model, Create, Update]"
                raise ValueError(msg)
        else:
            msg = "Model type must be specified via generic type parameters: CRUDBase[Model, Create, Update]"
            raise ValueError(msg)

    @abc.abstractmethod
    def get(self, *, id: int) -> ModelType | None:  # noqa: A002
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
        **filters: Any,
    ) -> PaginatedCRUDResult[ModelType]:
        """Get multiple records with pagination, filtering, and sorting."""

    @abc.abstractmethod
    def get_if_exist(self, *, id: int) -> ModelType:  # noqa: A002
        """Get record by ID or raise exception if it doesn't exist."""

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

    @abc.abstractmethod
    def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update existing record with new data."""

    @abc.abstractmethod
    def delete(self, *, id: int) -> ModelType:  # noqa: A002
        """Delete record by ID and return the deleted object."""
