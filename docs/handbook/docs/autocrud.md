---
title: AutoCRUD
description: How AutoCRUD works and how to use it effectively in Kwik
---

AutoCRUD gives you a complete, consistent CRUD surface for your models without the boilerplate. It pairs cleanly with Kwik’s dependencies and patterns so you can focus on business logic.

## Quick Mental Model {#mental-model}

- Define a small subclass of `AutoCRUD` per model.
- Pass a `context` (session + user) to every call.
- Get stable list endpoints with pagination, sorting, and filters out of the box.
- Let AutoCRUD set audit fields automatically when a user is available.

## The Generics Explained {#generics}

AutoCRUD’s type parameters define how it operates:

```python
from kwik.crud import AutoCRUD
from kwik.crud.context import UserCtx, NoUserCtx, Context

class MyCRUD(AutoCRUD[UserCtx, Model, CreateSchema, UpdateSchema, int]):
    ...
```

- `Ctx`: one of `UserCtx`, `NoUserCtx`, or `MaybeUserCtx` from `kwik.crud.context`.
- `Model`: your SQLAlchemy model (subclass of `kwik.models.Base`).
- `CreateSchema` / `UpdateSchema`: Pydantic models used for input.
- `PkType`: the primary key type, usually `int`.

Important:
- If your model has audit columns (`creator_user_id`, `last_modifier_user_id`), you must use `UserCtx`. AutoCRUD validates this at construction and raises a `ValueError` otherwise.
- AutoCRUD infers the model type from the generics. If you forget to specify them, it raises `ValueError` explaining what’s missing.

## Context and Audit Fields {#context-audit}

AutoCRUD inspects your model for audit columns:

- If found and you used `UserCtx`, it will set `creator_user_id` on `create()` and `last_modifier_user_id` on `update()` when `context.user` is present.
- If you try to use `NoUserCtx` with a model that has audit columns, AutoCRUD raises a `ValueError` at instantiation time.

Example behavior (simplified):

```python
db_obj = crud.create(obj_in=create_schema, context=context)  # sets creator_user_id if available
db_obj = crud.update(entity_id=42, obj_in=update_schema, context=context)  # sets last_modifier_user_id if available
```

## Listing: Pagination, Sorting, Filters {#listing}

`get_multi()` implements the standard list flow with validation:

```python
count, rows = crud.get_multi(
    context=context,
    skip=0,
    limit=100,
    sort=[("id", "desc")],
    status="active",  # any allowed filter field
)
```

Notes:
- Sorting uses a list of `(field, direction)` pairs. If not set, results default to primary key(s) ascending for stable pagination.
- Filters are passed as keyword arguments. AutoCRUD validates both sort and filter fields; invalid fields raise `ValueError` which Kwik maps to HTTP 400.
- In routes, prefer the `ListQuery` dependency to build these parameters consistently:

```python
from kwik.dependencies import ListQuery, UserContext
from kwik.schemas import Paginated, MyProfile

@router.get("/", response_model=Paginated[MyProfile])
def read_items(q: ListQuery, context: UserContext):
    total, data = crud.get_multi(context=context, **q)
    return {"total": total, "data": data}
```

## Core Methods {#methods}

- `get(entity_id, context)` → Model | None: Fetch by id.
- `get_if_exist(entity_id, context)` → Model: Fetch by id or raise `EntityNotFoundError`.
- `get_multi(context, skip=0, limit=100, sort=None, **filters)` → `(count, list[Model])`: List with pagination/sorting/filters.
- `create(obj_in, context)` → Model: Insert a new row; applies `creator_user_id` if available.
- `create_if_not_exist(obj_in, context, filters: dict[str, str], raise_on_error=False)` → Model: Insert or return existing; raises `DuplicatedEntityError` if `raise_on_error=True` and a match exists.
- `update(entity_id, obj_in, context)` → Model: Update a row; applies `last_modifier_user_id` if available.
- `delete(entity_id, context)` → Model: Delete and return the deleted object.

## Allowed Fields for List Queries {#allowed-fields}

By default, all mapped columns are allowed for sorting and filtering. To restrict these, set `list_allowed_fields` on your subclass:

```python
class ProductCRUD(AutoCRUD[UserCtx, Product, ProductCreate, ProductUpdate, int]):
    list_allowed_fields = {"id", "name", "status"}
```

Invalid fields cause `ValueError` → HTTP 400 via Kwik’s `value_error_handler`.

## Complete Example {#example}

Here’s a compact example mirroring the pattern from the home page.

```python
from decimal import Decimal
from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column

from kwik.crud import AutoCRUD
from kwik.crud.context import UserCtx
from kwik.models import Base, RecordInfoMixin

# Model with audit fields (from RecordInfoMixin)
class Product(Base, RecordInfoMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    price: Mapped[Decimal]
    status: Mapped[str]

class ProductCreate(BaseModel):
    name: str
    price: Decimal
    status: str = "active"

class ProductUpdate(BaseModel):
    name: str | None = None
    price: Decimal | None = None
    status: str | None = None

class ProductCRUD(AutoCRUD[UserCtx, Product, ProductCreate, ProductUpdate, int]):
    list_allowed_fields = {"id", "name", "status"}

crud_products = ProductCRUD(Product)
```

Use it in routes exactly like the Endpoints guide shows: inject `UserContext`, accept `ListQuery`, return `Paginated[...]` responses, and add `has_permission(...)` where appropriate.

## Tips {#tips}

- Mind the two “context” types: routes inject `UserContext` (dependency), while AutoCRUD generics use `UserCtx`/`NoUserCtx` (from `kwik.crud.context`). They’re related but not the same.
- Override methods to add business rules (e.g., soft‑delete, invariants). Keep signatures consistent and call `super()` when appropriate.
- If you need conflict‑free create, use `create_if_not_exist` with a filter dict that uniquely identifies the row.
- Keep list responses predictable: restrict `list_allowed_fields` to business‑meaningful fields.
