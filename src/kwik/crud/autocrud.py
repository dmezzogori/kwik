"""Complete CRUD operations class for database models."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, get_args

import pydantic
from sqlalchemy import func, select

from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var
from kwik.exceptions import DuplicatedEntityError, EntityNotFoundError
from kwik.models.base import Base
from kwik.typings import ParsedSortingQuery  # noqa: TC001

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.orm import Session


def _sort_query[ModelType: Base](
    *, model: type[ModelType], stmt: Select[tuple[ModelType]], sort: ParsedSortingQuery
) -> Select[tuple[ModelType]]:
    """Apply sorting parameters to SQLAlchemy select statement."""
    order_by = []
    for attr, order in sort:
        model_attr = getattr(model, attr)
        if order == "asc":
            order_by.append(model_attr.asc())
        else:
            order_by.append(model_attr.desc())
    return stmt.order_by(*order_by)


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


class AutoCRUD[ModelType: Base, CreateSchemaType: pydantic.BaseModel, UpdateSchemaType: pydantic.BaseModel]:
    """Complete CRUD implementation combining create, read, update, and delete operations."""

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
                msg = "Model type must be specified via generic type parameters: AutoCRUD[Model, Create, Update]"
                raise ValueError(msg)
        else:
            msg = "Model type must be specified via generic type parameters: AutoCRUD[Model, Create, Update]"
            raise ValueError(msg)

    def get(self, *, id: int) -> ModelType | None:  # noqa: A002
        """Get single record by primary key ID."""
        return self.db.get(self.model, id)

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters: object,
    ) -> tuple[int, list[ModelType]]:
        """Get multiple records with pagination, filtering, and sorting."""
        # Build base select statement
        stmt = select(self.model)

        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model, key) == value)

        # Get count for pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count: int = self.db.execute(count_stmt).scalar()

        # Apply sorting if provided
        if sort is not None:
            stmt = _sort_query(model=self.model, stmt=stmt, sort=sort)

        # Apply pagination and execute
        stmt = stmt.offset(skip).limit(limit)
        result = self.db.execute(stmt).scalars().all()

        return count, list(result)

    def get_if_exist(self, *, id: int) -> ModelType:  # noqa: A002
        """Get record by ID or raise NotFound exception if it doesn't exist."""
        r = self.get(id=id)
        if r is None:
            raise EntityNotFoundError(detail=f"Entity [{self.model.__tablename__}] with id={id} does not exist")
        return r

    def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """Create new record from schema data."""
        obj_in_data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)

        # Import here to avoid circular import
        from kwik.models.mixins import RecordInfoMixin  # noqa: PLC0415

        if self.user is not None and inspect.isclass(self.model) and issubclass(self.model, RecordInfoMixin):
            obj_in_data["creator_user_id"] = self.user.id

        db_obj = self.model(**obj_in_data)

        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        obj_in: CreateSchemaType,
        filters: dict[str, str],
        raise_on_error: bool = False,
    ) -> ModelType:
        """Create record if it doesn't exist, or return existing record."""
        # Build select statement with filters
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)

        obj_db: ModelType | None = self.db.execute(stmt).scalar_one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in)
        elif raise_on_error:
            raise DuplicatedEntityError
        return obj_db

    def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update existing record with new data."""
        update_data = obj_in.model_dump(exclude_unset=True)

        # Import here to avoid circular import
        from kwik.models.mixins import RecordInfoMixin  # noqa: PLC0415

        if self.user is not None and inspect.isclass(self.model) and issubclass(self.model, RecordInfoMixin):
            update_data["last_modifier_user_id"] = self.user.id

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)

        return db_obj

    def delete(self, *, id: int) -> ModelType:  # noqa: A002
        """Delete record by ID and return the deleted object."""
        obj: ModelType = self.db.get(self.model, id)

        self.db.delete(obj)
        self.db.flush()
        return obj


__all__ = [
    "AutoCRUD",
    "NoDatabaseConnectionError",
]
