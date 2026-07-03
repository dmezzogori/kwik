---
title: User model
description: Extend Kwik's user identity with your own columns and relationships via the typed Kernel
---

# Extending the User model

Every Kwik application has exactly one user identity, mapped to a single `users`
table. In earlier releases that table was a fixed `User` model you could not
touch, so applications that needed extra fields on the user (a company, a set of
skills, an "external" flag) reached for a **second table** with a 1:1 foreign key
back to `users` and hybrid-property proxying. That workaround is expensive: dual
IDs, extra joins, scalar-subquery overhead, foreign keys split across two targets,
duplicated Pydantic fields, and create/update/delete logic that has to keep two
rows in sync.

Kwik 2.0 removes the need for all of that. You compose **your own** user model
from a mixin, register it once through a typed `Kernel`, and Kwik wires its
authentication, CRUD, routers, and testing utilities to your class. The result is
a **single `users` table** — no side table, no proxying, no joins — and your
endpoints see the user as your concrete type, with your custom fields
autocompleting and type-checked.

!!! info "One user model per process"
    SQLAlchemy's shared `Base.metadata` cannot map two classes to the same table,
    and a mapped class cannot be un-mapped. Kwik therefore allows **exactly one**
    user model per process and makes that explicit: construct your `Kernel` once,
    before importing Kwik's routers or running the app. A second `Kernel` raises a
    `RuntimeError`.

## Composing a custom model

Subclass `Base` and `UserMixin`. `UserMixin` contributes the auth-essential
columns and relationships (`id`, `name`, `surname`, `email`, `hashed_password`,
`is_active`, plus `roles` and the `permissions` hybrid). Importing it maps
nothing on its own — your class is the one that becomes the `users` table, so it
**must** declare `__tablename__ = "users"`:

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from kwik.models import Base, UserMixin


class AppUser(Base, UserMixin):
    __tablename__ = "users"  # required: kwik's foreign keys reference this table

    company: Mapped[str] = mapped_column(String, default="", nullable=False)
    external: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

Add whatever columns and relationships your domain needs. The only hard rules —
both enforced when you build the `Kernel` — are that the class subclasses
`Base` and `UserMixin` and that it maps to the `users` table. The `UserTrackingMixin`
audit columns (`creator_user_id`, `last_modifier_user_id`) still point at
`users.id`, `UserRole` still joins `users` to `roles`, and `ApiKey` still keys on
`users.id` — keeping the table name fixed leaves the rest of the schema untouched.

## Registering the Kernel and typed aliases

Create the `Kernel` in a module that is imported **before** any router module —
a small `app/kernel.py` is the conventional home. Registering the model also
builds a typed `crud_users` for it and claims the process-wide slot:

```python
from typing import Annotated

from fastapi import Depends

import kwik
from kwik.crud.context import Context

from app.models import AppUser
from app.schemas import AppUserProfile, AppUserRegistration, AppUserUpdate

kernel = kwik.Kernel(
    user_model=AppUser,
    schemas=kwik.UserSchemas(
        profile=AppUserProfile,
        registration=AppUserRegistration,
        update=AppUserUpdate,
    ),
)

# App-side typed aliases — one line each, statically valid:
CurrentUser = Annotated[AppUser, Depends(kernel.get_current_user)]
UserContext = Annotated[Context[AppUser], Depends(kernel.get_user_context)]
```

Those two aliases are the payoff of the typed design. `kernel.get_current_user`,
`kernel.get_resolved_user`, and `kernel.get_user_context` are typed against your
model, so `CurrentUser` resolves to `AppUser` and `UserContext` to
`Context[AppUser]`. In an endpoint, `user: CurrentUser` gives you `user.company`
with autocompletion and type-checking; `context: UserContext` carries an
`AppUser`-typed `context.user`. Import these aliases from `app/kernel.py`
throughout your endpoints instead of Kwik's `UserMixin`-typed defaults.

!!! note "Why the aliases live in your app"
    An `Annotated[...]` alias must name the concrete class to be statically valid,
    so the aliases are declared in your application rather than derived from the
    kernel by magic. The kernel's guarantee is that its dependency callables are
    *typed* against your model, which is what gives the one-line aliases real
    type-checker backing.

## Building the app

Assemble Kwik's built-in routers from the kernel with `create_api_router()`, add
your own routers, and hand the result to `Kwik`:

```python
import kwik
from kwik.settings import BaseKwikSettings

from app.kernel import kernel
from app.api import my_router

api_router = kernel.create_api_router()  # login/users/roles/permissions
api_router.include_router(my_router)

app = kwik.Kwik(settings=BaseKwikSettings(), api_router=api_router)
```

Each built-in router is individually opt-out-able through a boolean flag, so you
can drop any subset and supply your own:

```python
# e.g. keep login + users, replace roles/permissions with your own routers
api_router = kernel.create_api_router(roles=False, permissions=False)
```

`create_api_router(*, login=True, users=True, roles=True, permissions=True)`
returns a plain FastAPI `APIRouter`; the `users`, `login`, and `roles` routers are
built from the kernel's model and schemas, while `permissions` (which needs no
user schemas) is included as-is.

## The schemas contract

`UserSchemas` bundles the three Pydantic types Kwik binds to the user endpoints.
The simplest way to define them is to subclass Kwik's stock schemas and add your
custom fields:

```python
from kwik.schemas import UserProfile, UserProfileUpdate, UserRegistration


class AppUserProfile(UserProfile):        # response model
    company: str
    external: bool


class AppUserRegistration(UserRegistration):  # create payload
    company: str = ""
    external: bool = False


class AppUserUpdate(UserProfileUpdate):   # update payload
    company: str | None = None
    external: bool | None = None
```

The contract Kwik validates at `Kernel` construction:

- **`profile`** must enable `model_config["from_attributes"]` so it can serialize
  ORM instances. `UserProfile` inherits this from `ORMMixin`, so subclassing it is
  enough.
- **`registration`** must carry the base registration fields (`name`, `surname`,
  `email`, `is_active`) **plus a `password` field**. `UserRegistration` already
  declares all of them; add your custom columns as fields.
- **`update`** carries the updatable fields, all optional.

Custom registration fields flow straight into your custom columns: `create()`
calls `obj_in.model_dump()`, pops `password` (hashing it into `hashed_password`),
and passes the remaining keys to `AppUser(**data)`. So any field you add to the
registration schema whose name matches a mapped column is persisted with no extra
wiring. Schemas are optional — omit the `schemas=` argument and Kwik uses its
stock `UserProfile` / `UserRegistration` / `UserProfileUpdate`, which is exactly
what a model with no extra fields wants.

## Seeding the first superuser

`kwik.seeding.create_first_superuser` idempotently creates the admin role, every
`Permissions` enum value, the superuser from `settings.FIRST_SUPERUSER` /
`FIRST_SUPERUSER_PASSWORD`, and the role assignment — all through the kernel's
CRUD, so it works transparently with your model. Call it from the `Kwik(seed_db=...)`
hook:

```python
from kwik.seeding import create_first_superuser


def seed_db(session, settings):  # Kwik calls the hook with (session, settings)
    create_first_superuser(session=session, settings=settings)


app = kwik.Kwik(settings=settings, api_router=api_router, seed_db=seed_db)
```

If your model has non-null custom columns that your registration schema does not
default, pass them as keyword arguments — they are forwarded to the registration
schema:

```python
create_first_superuser(session=session, settings=settings, company="ACME", external=False)
```

Because `AppUserRegistration` above defaults `company` and `external`, seeding
needs no extra fields here; `**extra_fields` is the escape hatch for columns your
registration schema requires without a default.

## Testing a custom user model

The one-kernel-per-process rule shapes how you test. Construct the `Kernel` at
**import time** in your `conftest.py`, before any fixture runs, and run the
custom-user tests as their **own pytest session** — never collected alongside
tests that use Kwik's `DefaultUser`.

```python
# tests/conftest.py
from kwik import Kernel, UserSchemas

from app.models import AppUser
from app.schemas import AppUserProfile, AppUserRegistration, AppUserUpdate

# Constructed at module import — before Kwik's fixtures build the schema.
KERNEL = Kernel(
    user_model=AppUser,
    schemas=UserSchemas(
        profile=AppUserProfile,
        registration=AppUserRegistration,
        update=AppUserUpdate,
    ),
)
```

Enable Kwik's fixtures for an out-of-tree suite by loading the plugin on the
command line, and disable xdist parallelism so the suite runs in a single process:

```bash
uv run pytest tests -p kwik.testing.fixtures -n 0
```

The `engine` fixture calls `get_kernel()` before `Base.metadata.create_all(...)`,
so your registered model is the one mapped and created. The `admin_user` fixture
is built on `create_first_superuser`, so fixtures and production share one code
path.

`Scenario` and `user_factory` accept `extra_fields`, validated through your
registered registration schema and persisted into your custom columns. Passwords
chosen during a build are returned on `ScenarioResult.passwords`; hand them to
`IdentityAwareTestClient.register_passwords(...)` so it can authenticate those
users:

```python
from kwik.testing import IdentityAwareTestClient, Scenario


def test_custom_field_roundtrip(session, admin_user, identity_aware_client):
    scenario = (
        Scenario()
        .with_user(name="acme", email="dev@acme.test", extra_fields={"company": "ACME", "external": True})
        .build(session=session, admin_user=admin_user)
    )
    identity_aware_client.register_passwords(scenario.passwords)

    response = identity_aware_client.get_as(scenario.users["acme"], "/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["company"] == "ACME"
```

If you want the type-checker to enforce the typing guarantee, add a small
`assert_type` contract module (as Kwik's own `tests_custom_user/test_typing_contract.py`
does) and run `pyright` against it.

## Migrating from the 1.x two-table pattern

If you are coming from the pre-2.0 pattern of a side table (e.g. `resources`) with
a 1:1 FK to `users`, the migration is mechanical:

1. **Define your model.** Create `AppUser(Base, UserMixin)` with
   `__tablename__ = "users"`, moving the side table's columns and relationships
   onto it.
2. **Register the kernel.** Add `app/kernel.py` with the `Kernel`, `UserSchemas`,
   and the typed `CurrentUser` / `UserContext` aliases.
3. **Write one Alembic migration.** Add the new columns to `users`; rewrite every
   foreign key that pointed at the side table's id to reference `users.id`
   (data-migrate through the side table's `user_id`); drop the side table.
4. **Delete the side model.** Remove the side-table model, its hybrid proxies, any
   `current_resource`-style dependency, and the dual-entity CRUD coordination —
   replace them with `CurrentUser` and direct field access.
5. **Switch router assembly.** Replace the removed `api_router` singleton with
   `kernel.create_api_router(...)` plus your own routers, and replace
   `from kwik.crud import crud_users` with `kernel.crud_users`
   (typed `CRUDUsers[AppUser]`).
6. **Update seeding.** Call `kwik.seeding.create_first_superuser(...)` from your
   `seed_db` hook.

## Zero-config applications

If your application does not need any extra user fields, there is **nothing to
do**. Never touch the kernel: on first internal use, Kwik materializes a default
kernel wired to its built-in `DefaultUser` model and stock schemas. `DefaultUser`
is imported lazily and only then, so it never collides with a custom model in
`Base.metadata`. Kwik's module-level aliases — `kwik.current_user`,
`kwik.resolved_user`, `kwik.UserContext`, `kwik.NoUserContext` — are typed against
`UserMixin` and resolve the active kernel at request time, so the batteries-included
experience works exactly as before.
