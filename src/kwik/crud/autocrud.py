"""Complete CRUD operations class for database models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, get_args

from pydantic import BaseModel
from sqlalchemy import func, select

from kwik.exceptions import DuplicatedEntityError, EntityNotFoundError
from kwik.models.base import Base
from kwik.typings import ParsedSortingQuery  # noqa: TC001

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.orm import Session

    from kwik.models import User


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


@dataclass(slots=True, frozen=True)
class Context[U: (None, User, User | None)]:
    session: Session
    user: U


# Narrow, readable aliases for APIs
type UserCtx = Context[User]
type MaybeUserCtx = Context[User | None]
type NoUserCtx = Context[None]


# TODO: rename id methods' argument
class AutoCRUD[Ctx: Context, ModelType: Base, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel]:
    """Complete CRUD implementation combining create, read, update, and delete operations."""

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
                self.model = args[1]
            else:
                msg = "Model type must be specified via generic type parameters: AutoCRUD[Model, Create, Update]"
                raise ValueError(msg)
        else:
            msg = "Model type must be specified via generic type parameters: AutoCRUD[Model, Create, Update]"
            raise ValueError(msg)

        # TODO: check if hasattr works on SQLAlchemy attributes
        # TODO: we can already check for consistency: if self.record_creator_user_id is True, then Ctx must be UserCtx, otherwise the subclass is wrongly setup
        self.record_creator_user_id = hasattr(self.model, "creator_user_id")
        self.record_modifier_user_id = hasattr(self.model, "last_modifier_user_id")

    def get(self, *, id: int, context: Ctx) -> ModelType | None:  # noqa: A002
        """Get single record by primary key ID."""
        return context.session.get(self.model, id)

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        context: Ctx,
        **filters: str | float | bool,
    ) -> tuple[int | None, list[ModelType]]:
        """Get multiple records with pagination, filtering, and sorting."""
        # Build base select statement
        stmt = select(self.model)

        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model, key) == value)

        # Get count for pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count = context.session.execute(count_stmt).scalar()

        # Apply sorting if provided
        if sort is not None:
            stmt = _sort_query(model=self.model, stmt=stmt, sort=sort)

        # Apply pagination and execute
        stmt = stmt.offset(skip).limit(limit)
        result = context.session.execute(stmt).scalars().all()

        return count, list(result)

    def get_if_exist(self, *, id: int, context: Ctx) -> ModelType:  # noqa: A002
        """Get record by ID or raise NotFound exception if it doesn't exist."""
        r = self.get(id=id, context=context)
        if r is None:
            raise EntityNotFoundError(detail=f"Entity [{self.model.__tablename__}] with id={id} does not exist")
        return r

    def create(self, *, obj_in: CreateSchemaType, context: Ctx) -> ModelType:
        """Create new record from schema data."""
        obj_in_data = obj_in.model_dump()

        if context.user is not None and self.record_creator_user_id:
            obj_in_data["creator_user_id"] = context.user.id

        db_obj = self.model(**obj_in_data)

        context.session.add(db_obj)
        context.session.flush()
        context.session.refresh(db_obj)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        obj_in: CreateSchemaType,
        context: Ctx,
        filters: dict[str, str],
        raise_on_error: bool = False,
    ) -> ModelType:
        """Create record if it doesn't exist, or return existing record."""
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)

        obj_db: ModelType | None = context.session.execute(stmt).scalar_one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in, context=context)
        elif raise_on_error:
            raise DuplicatedEntityError
        return obj_db

    def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType, context: Ctx) -> ModelType:
        """Update existing record with new data."""
        update_data = obj_in.model_dump(exclude_unset=True)

        if context.user is not None and self.record_modifier_user_id:
            update_data["last_modifier_user_id"] = context.user.id

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        context.session.add(db_obj)
        context.session.flush()
        context.session.refresh(db_obj)

        return db_obj

    # TODO: dedice wheter to use id or db_obj in update and delete method, and use it consistently
    def delete(self, *, id: int, context: Ctx) -> ModelType | None:  # noqa: A002
        """Delete record by ID and return the deleted object."""
        obj = self.get(id=id, context=context)

        context.session.delete(obj)
        context.session.flush()
        return obj


__all__ = ["AutoCRUD", "NoDatabaseConnectionError"]
