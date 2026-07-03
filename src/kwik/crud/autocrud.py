"""Complete CRUD operations class for database models."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, TypeVar, get_args

from pydantic import BaseModel
from sqlalchemy import func, inspect, select

from kwik.exceptions import DuplicatedEntityError, EntityNotFoundError
from kwik.models import Base

from .context import Context

if TYPE_CHECKING:
    from sqlalchemy import Select

    from kwik.dependencies.sorting_query import ParsedSortingQuery


def _sort_query[ModelType: Base](
    *, model: type[ModelType], stmt: Select[tuple[ModelType]], sort: ParsedSortingQuery
) -> Select[tuple[ModelType]]:
    """Apply sorting parameters to SQLAlchemy select statement with basic validation."""
    mapper_columns = inspect(model).columns
    order_by = []
    for attr, order in sort:
        if attr not in mapper_columns:
            msg = f"Invalid sort field '{attr}' for model {model.__name__}"
            raise ValueError(msg)
        model_attr = getattr(model, attr)
        if order == "asc":
            order_by.append(model_attr.asc())
        else:
            order_by.append(model_attr.desc())
    return stmt.order_by(*order_by)


def _ctx_requires_user(ctx_type: object) -> bool:
    """Return True when a Context type parameter guarantees a non-None user."""
    resolved = getattr(ctx_type, "__value__", ctx_type)  # unwrap PEP 695 `type` aliases
    args = get_args(resolved)
    if not args:
        return False
    user_type = args[0]
    if user_type is type(None):
        return False
    return type(None) not in get_args(user_type)


class NoDatabaseConnectionError(Exception):
    """Raised when no database connection is available."""


class AutoCRUD[Ctx: Context, ModelType: Base, CreateSchemaType: BaseModel, UpdateSchemaType: BaseModel, PkType]:
    """Complete CRUD implementation combining create, read, update, and delete operations."""

    model: type[ModelType]
    # Optional allowlist of fields exposed for list filtering/sorting
    list_allowed_fields: ClassVar[set[str] | None] = None

    def __init__(self, *, model: type[ModelType] | None = None) -> None:
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        The model type is extracted from the generic type parameters, or passed
        explicitly via ``model=`` (required when the subclass is itself generic
        over the model, e.g. the kernel-owned users CRUD).
        """
        bases = getattr(self, "__orig_bases__", None)
        if model is not None:
            self.model = model
        else:
            if bases is None or not get_args(bases[0]):
                msg = "Model type must be specified via generic type parameters: AutoCRUD[Model, Create, Update]"
                raise ValueError(msg)
            candidate = get_args(bases[0])[1]
            if isinstance(candidate, TypeVar):
                msg = (
                    "Model type is a type variable; pass the concrete model explicitly: "
                    f"{type(self).__name__}(model=MyModel)"
                )
                raise TypeError(msg)
            self.model = candidate

        # Check for audit trail fields using SQLAlchemy introspection
        model_columns = inspect(self.model).columns
        self.record_creator_user_id = "creator_user_id" in model_columns
        self.record_modifier_user_id = "last_modifier_user_id" in model_columns

        # Determine allowed fields for list queries
        if self.list_allowed_fields is None:
            # default to all mapped columns
            self._list_allowed_fields = set(model_columns.keys())
        else:
            self._list_allowed_fields = set(self.list_allowed_fields)

        # Validate consistency: audit fields require a Context type with a non-optional user
        if self.record_creator_user_id or self.record_modifier_user_id:
            ctx_type = get_args(bases[0])[0] if bases is not None and get_args(bases[0]) else None
            if ctx_type is None or not _ctx_requires_user(ctx_type):
                ctx_name = getattr(ctx_type, "__name__", repr(ctx_type))
                msg = (
                    f"Model {self.model.__name__} has audit trail fields (creator_user_id/last_modifier_user_id) "
                    f"but its Context parameter ({ctx_name}) allows a None user. "
                    f"Use a Context with a non-optional user type (e.g. UserCtx) as the first generic parameter."
                )
                raise ValueError(msg)

    def get(self, *, entity_id: PkType, context: Ctx) -> ModelType | None:
        """Get single record by primary key entity ID."""
        return context.session.get(self.model, entity_id)

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        context: Ctx,
        **filters: str | float | bool,
    ) -> tuple[int, list[ModelType]]:
        """Get multiple records with pagination, filtering, and sorting."""
        # Build base select statement
        stmt = select(self.model)

        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if key not in self._list_allowed_fields:
                    msg = f"Invalid filter field '{key}' for model {self.model.__name__}"
                    raise ValueError(msg)
                stmt = stmt.where(getattr(self.model, key) == value)

        # Get count for pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count = context.session.execute(count_stmt).scalar() or 0

        # Apply sorting if provided, otherwise default to primary key(s) ascending for stable pagination
        if sort:
            # Validate sort fields against allowlist
            for key, _ in sort:
                if key not in self._list_allowed_fields:
                    msg = f"Invalid sort field '{key}' for model {self.model.__name__}"
                    raise ValueError(msg)
            stmt = _sort_query(model=self.model, stmt=stmt, sort=sort)
        else:
            pk_cols = inspect(self.model).primary_key
            if pk_cols:
                stmt = stmt.order_by(*[c.asc() for c in pk_cols])

        # Apply pagination and execute
        stmt = stmt.offset(skip).limit(limit)
        result = context.session.execute(stmt).scalars().all()

        return count, list(result)

    def get_if_exist(self, *, entity_id: PkType, context: Ctx) -> ModelType:
        """Get record by entity ID or raise NotFound exception if it doesn't exist."""
        r = self.get(entity_id=entity_id, context=context)
        if r is None:
            raise EntityNotFoundError(detail=f"Entity [{self.model.__tablename__}] with id={entity_id} does not exist")
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

    def update(self, *, entity_id: PkType, obj_in: UpdateSchemaType, context: Ctx) -> ModelType:
        """Update existing record by entity ID with new data."""
        db_obj = self.get_if_exist(entity_id=entity_id, context=context)
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

    def delete(self, *, entity_id: PkType, context: Ctx) -> ModelType:
        """Delete record by entity ID and return the deleted object."""
        obj = self.get_if_exist(entity_id=entity_id, context=context)

        context.session.delete(obj)
        context.session.flush()
        return obj


__all__ = ["AutoCRUD", "NoDatabaseConnectionError"]
