# kwik User Model Extensibility — Typed Kernel Design

**Issue:** [teban#265](https://github.com/kheperer-labs/teban/issues/265)
**Consumer:** [teban#266](https://github.com/kheperer-labs/teban/issues/266) (Resource/User consolidation)
**Supersedes:** teban `docs/superpowers/specs/2026-05-11-kwik-user-model-extensibility-design.md` (Mixin + global registry approach)
**Repository:** kwik — branch `feature/user-model-extensibility`
**Target release:** kwik 2.0.0
**Date:** 2026-07-02

## Problem

kwik defines a concrete `User` model with auth-essential fields (`email`, `hashed_password`, `is_active`, `name`, `surname`, `roles`). Consuming applications need to add domain-specific fields and relationships to the user identity. Teban's current workaround is a separate `resources` table with a 1:1 FK to `users` and hybrid-property proxying, which causes dual-ID confusion, extra joins, scalar-subquery overhead, split FK targeting across the schema (some tables key on `users.id`, others on `resources.id`), duplicated Pydantic fields, and dual-entity CRUD coordination in create/update/delete.

kwik must let a consuming app extend the User model — single table, no joins, no proxying — while preserving kwik's auth, CRUD, router, and testing functionality.

## Constraints and Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Compatibility budget | Breaking OK — major bump to **2.0.0** | kwik is pre-release in spirit; teban (the sole production consumer) migrates deliberately via teban#266. No compat shims, no lazy `__getattr__` aliases. |
| Static typing for consumers | **First-class requirement** | Teban endpoints must see `current_user` as `TebanUser` with custom fields autocompleting and type-checked. Drives the generic-kernel design over a stringly-typed registry. |
| Scope | **Broader 2.0 cleanup** anchored on user extensibility | Also fixes adjacent extension seams: router composition opt-out, first-superuser seeding battery, testing-utility cleanup. No unrelated refactors. |
| User model handoff | Generic `Kernel[UserT]` object, created once by the app | Explicit, typed, fails loudly at construction. Public API is the kernel; a minimal internal registry is plumbing only. |
| ORM strategy | Mixin composition (`Base + UserMixin`), **not** SQLAlchemy inheritance | Joined/single-table inheritance reintroduces joins or discriminators — the exact problem being solved. Flask-Security-proven pattern. |
| Table name | Custom model **must** declare `__tablename__ = "users"` | `UserTrackingMixin`, `UserRole`, and `ApiKey` FK to the literal `"users.id"` string; keeping the table name fixed leaves the rest of the schema untouched. Enforced at kernel construction. |
| Models per process | Exactly one user model per process | Not a design choice: SQLAlchemy's shared `Base.metadata` cannot map two classes to the same table, and a mapped class cannot be unmapped. The kernel makes this loud instead of accidental. |
| Schema handling | App registers Pydantic schemas alongside the model (`UserSchemas`) | Explicit, no auto-generation magic. Defaults apply when not provided. |
| Settings | No `AUTH_USER_MODEL`-style setting | The kernel *is* the configuration; a string import path in settings would undercut the typing story. |

### Rejected alternatives

- **A — Global `kwik.configure()` registry (the 2026-05-11 spec).** Smallest surface and closest to Django, but `get_user_model()` returns an unparameterized `type`: `current_user` would be typed `UserMixin`, forcing app-side re-annotation by hand. Global one-shot mutable state with import-order sensitivity, and no structural anchor for the 2.0 cleanup.
- **B — Fully explicit generic components, zero global state (FastAPI-Users style).** Best-in-class purity, but SQLAlchemy's declarative layer still needs a global hook for relationship targets (`Role.users`, `ApiKey.user`), so a hidden registry survives anyway; heaviest inversion-of-control refactor through `security`/api-key/permissions; most consumer boilerplate, fighting kwik's batteries-included identity.
- **C (chosen) — Typed kernel over a minimal internal registry.** B's typing with A's ergonomics; accepts the process-global reality and sets it exactly once, loudly.

## Detailed Design

### 1. Model layer

**`models/user_mixin.py` (new)** — `UserMixin`, a pure mixin (importing it maps nothing):

- Columns: `id` (PK), `name`, `surname`, `email` (unique), `hashed_password`, `is_active` — as `mapped_column` attributes.
- `roles` relationship (secondary `"users_roles"`) and the `permissions` hybrid property as `@declared_attr`s.
- No mapped class may be imported at module scope; `Role`/`UserRole`/`Permission` references go under `TYPE_CHECKING` or inside lambdas/strings in relationship definitions.

**`models/default_user.py` (new)** — `DefaultUser(Base, UserMixin)` with `__tablename__ = "users"`. Imported **only** by the default-kernel fallback, never eagerly. This prevents duplicate-`__tablename__` mapping collisions when an app defines its own user class.

**`models/mixins.py`** — the existing audit-trail `UserMixin` (`creator_user_id`, `last_modifier_user_id`) is **renamed to `UserTrackingMixin`** (no deprecation alias — 2.0). `RecordInfoMixin(TimeStampsMixin, UserTrackingMixin)` composition unchanged.

**`models/user.py`** — keeps `Role`, `UserRole`, `Permission`, `RolePermission`. The concrete `User` class is deleted. `Role.users` becomes a `@declared_attr` whose relationship target is a **callable** (`lambda: get_kernel().user_model`), never an eager call — `@declared_attr` bodies run at class-definition time, before any kernel exists.

**`models/api_key.py`** — `ApiKey.user` relationship target resolved the same way (callable via the kernel); the `ForeignKey("users.id")` string is already table-based and stays.

**Consuming app model:**

```python
class TebanUser(Base, UserMixin):
    __tablename__ = "users"          # required, validated by the kernel

    company: Mapped[str] = mapped_column(String, default="", nullable=False)
    external: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skills: Mapped[list[Skill]] = relationship(...)
    # ...departments, rates, etc.
```

### 2. Kernel — public API and typing story

**`kwik/kernel.py` (new)** — `Kernel[UserT: UserMixin]`, plus `UserSchemas`:

```python
@dataclass(frozen=True)
class UserSchemas:
    profile: type[BaseModel]        # response model
    registration: type[BaseModel]   # create payload
    update: type[BaseModel]         # update payload


class Kernel[UserT: UserMixin]:
    def __init__(self, *, user_model: type[UserT], schemas: UserSchemas | None = None) -> None:
        # 1. validate (see §10), 2. claim the process-wide slot, 3. build crud_users, 4. resolve schemas
        ...

    user_model: type[UserT]
    schemas: UserSchemas
    crud_users: CRUDUsers[UserT]

    # FastAPI dependency callables (bound methods; FastAPI resolves sub-deps from their signatures)
    def get_current_user(...) -> UserT: ...
    def get_resolved_user(...) -> UserT: ...          # JWT-or-API-key path
    def get_user_context(...) -> Context[UserT]: ...

    # Router factories (see §7)
    def create_users_router(self) -> AuthenticatedRouter: ...
    def create_login_router(self) -> APIRouter: ...
    def create_roles_router(self) -> AuthenticatedRouter: ...
    def create_api_router(self, *, login: bool = True, users: bool = True,
                          roles: bool = True, permissions: bool = True) -> APIRouter: ...
```

**Consumer usage:**

```python
# teban/kernel.py — imported before any router module
kernel = Kernel(                                   # inferred: Kernel[TebanUser]
    user_model=TebanUser,
    schemas=UserSchemas(profile=TebanUserProfile,
                        registration=TebanUserRegistration,
                        update=TebanUserUpdate),
)

# App-side typed aliases — one line each, statically valid:
CurrentUser = Annotated[TebanUser, Depends(kernel.get_current_user)]
UserContext = Annotated[Context[TebanUser], Depends(kernel.get_user_context)]
```

**Typing subtlety (accepted):** an `Annotated` alias must name the concrete class to be statically valid, so aliases live in the app, not derived from the kernel by magic. The kernel's guarantee is that its dependency callables are *typed* against `UserT` (so the one-line aliases have real type-checker backing) and that `kernel.crud_users.get(...)` returns a typed `UserT`.

**Zero-config apps:** never touch the kernel. On first internal resolution, kwik materializes a default kernel wired to `DefaultUser` and stock schemas. kwik exports ready-made module-level aliases (`current_user`, `resolved_user`, `UserContext`, `MaybeUserContext`, `NoUserContext`) typed against `UserMixin`; their underlying dependency functions call `get_kernel()` at request time, so nothing is mapped eagerly at import.

### 3. Internal registry (`kwik/kernel.py`, private)

A module-level slot holding the active `Kernel | None`:

- `get_kernel()` → returns the active kernel; if none, lazily imports `DefaultUser`, constructs the default kernel, claims the slot.
- `Kernel.__init__` claims the slot; raises `RuntimeError` if already claimed (by another kernel or the materialized default) with an actionable message ("construct your Kernel before importing kwik routers / running the app").
- `_reset_for_testing()` clears the slot — safe **only** if no model was mapped by the outgoing kernel (registry unit tests); switching mapped user models mid-process is impossible and documented as such.
- Only kwik internals call `get_kernel()`; consuming apps hold their own `kernel` reference.

### 4. CRUD

**`crud/autocrud.py`** — `AutoCRUD.__init__` accepts an optional explicit `model: type[ModelType] | None = None`. When given, it bypasses `__orig_bases__` generic-args inference; introspection (audit columns, `list_allowed_fields`) runs in `__init__` as today. No lazy-property machinery: by the time a kernel exists, the model is in hand.

**`crud/users.py`** — `_CRUDUsers` becomes `CRUDUsers[UserT: UserMixin](AutoCRUD[MaybeUserCtx, UserT, BaseModel, BaseModel, int])`, generic over the model (runtime-safe: type parameters, no concrete `User` import). The kernel constructs it as `CRUDUsers(model=user_model)`. Changes:

- Every `select(User)` / `User(...)` becomes `self.model` (`get_by_email`, `create_if_not_exist`, etc.).
- `create()` switches from a hard-coded field list to `obj_in.model_dump()` → pop `password`, insert `hashed_password=get_password_hash(...)`, then `self.model(**data)` — so custom registration fields flow into custom columns.
- The module-level `crud_users` singleton is **removed**. kwik internals use `get_kernel().crud_users`; apps use `kernel.crud_users` (typed `CRUDUsers[TebanUser]`).

**`crud/roles.py`** — user-join queries (`get_users_without`, `assign_user`, `remove_user`) resolve the model via `get_kernel().user_model` inside method bodies.

### 5. Context

**`crud/context.py`** — `Context`'s type parameter changes from the constrained form `(None, User, User | None)` to **bounded**: `Context[U: UserMixin | None]`, making `Context[TebanUser]` legal. kwik aliases re-point: `UserCtx = Context[UserMixin]`, `MaybeUserCtx = Context[UserMixin | None]`, `NoUserCtx = Context[None]`.

**AutoCRUD audit validation** — the current check "ctx type must be `UserCtx`" relaxes to "the ctx's user type argument must not include `None`" (e.g., `type(None) not in get_args(...)` on the resolved parameter), so app-defined `Context[TebanUser]` CRUD classes pass while audit-writing CRUDs with nullable-user contexts still fail loudly.

### 6. Dependencies and security

- **`dependencies/users.py`** — `_get_current_user` / `_resolve_current_user` resolve via `get_kernel().crud_users`; module-level aliases typed against `UserMixin` (see §2). `Kernel.get_current_user`/`get_resolved_user` are thin bound methods over the same logic, typed `-> UserT`.
- **`dependencies/context.py`** — context dependencies built the same way; kernel exposes the typed variants.
- **`dependencies/api_key.py`** — `session.get(get_kernel().user_model, api_key.user_id)`.
- **`dependencies/permissions.py`** — `has_permission` goes through `get_kernel().crud_users`.
- **`security.py`** — `authenticate_from_token` and `verify_password_reset_token` resolve via `get_kernel().crud_users`; return types annotated `UserMixin`. Token creation/decoding unchanged (`sub` remains the integer user id).

### 7. Router factories

`users`, `login`, and `roles` routers become factory methods on the kernel; `permissions_router` stays module-level (no user schemas). Factories bind **both** directions from `kernel.schemas`:

- Response: `response_model=schemas.profile`, `Paginated[schemas.profile]`, etc.
- Request: endpoint parameters annotated with `schemas.registration` / `schemas.update` inside the factory closure.

All current endpoint behavior (impersonation, password change/reset, admin reset, role assign/remove) is preserved, just resolved through the kernel.

**Implementation gotcha (hard requirement):** router-factory modules must **not** use `from __future__ import annotations`. Deferred annotations turn closure-bound schema types into strings that `get_type_hints` cannot resolve (closure locals are invisible to it), silently breaking FastAPI request-body binding. Add a targeted ruff/noqa exception if the lint config demands the future import.

### 8. 2.0 surface cleanup

**Router composition.** The pre-built `api_router` singleton (`api/api.py`) is deleted — it pre-included login/users/roles/permissions with no opt-out. Replacement: `kernel.create_api_router(login=..., users=..., roles=..., permissions=...)`; apps append their own routers to the result or cherry-pick individual factories. `kwik.api_router` and module-level router exports (`users_router`, `login_router`, `roles_router`) are removed. `__main__.py` (dev-server entry point) uses the default kernel internally.

**Public exports.** `kwik`: `Kernel`, `UserSchemas`, `UserMixin`, `Kwik`, `run`, `testing`, plus default-kernel aliases (`current_user`, `resolved_user`, `UserContext`, ...). `kwik.models`: `Base`, `UserMixin`, `UserTrackingMixin`, `RecordInfoMixin`, `TimeStampsMixin`, `Role`, `UserRole`, `Permission`, `RolePermission`, `ApiKey` — **no `User` name at all**; `DefaultUser` is never eagerly imported and has no top-level alias. Stale references fail at import instead of resolving to the wrong thing.

**Seeding battery (new `kwik/seeding.py`).** `create_first_superuser(session, settings, **extra_fields)` — idempotently creates the admin role, all `Permissions` enum values, the superuser from `FIRST_SUPERUSER`/`FIRST_SUPERUSER_PASSWORD`, and the role assignment, through the kernel's crud. `**extra_fields` covers custom models with extra non-null columns. `Kwik(seed_db=...)` remains the hook; this battery is what apps (and kwik's own fixtures) call from it.

**Settings.** `BaseKwikSettings` unchanged structurally; no new settings.

**Docs.** Handbook quickstart rewritten around the kernel (also fixing the incorrect `AutoCRUD(Customer)` positional-argument example); new "Extending the User model" page; migration guide (§9).

### 9. Testing framework

- **`testing/fixtures/core_fixtures.py`** — the `engine` fixture calls `get_kernel()` before `Base.metadata.create_all()` so the active user model is mapped in time. `admin_user` is rewritten on top of `kwik.seeding.create_first_superuser` (fixtures and production share one code path).
- **`testing/scenario.py`** — `UserSpec` gains `extra_fields: dict[str, Any]`. `Scenario.build()` constructs the user payload by instantiating **the kernel's registered registration schema** with base + extra fields — validation for free, and the fields flow through `create()`'s `model_dump()` into custom columns. Relationship attributes are out of scope; apps seed those post-creation with their own fixtures.
- **`testing/fixtures/factories.py`** — `user_factory` accepts and forwards `extra_fields`.
- **`testing/client.py`** — `IdentityAwareTestClient` drops the hard-coded password-by-email table in favor of resolving passwords from the scenario/factory results (which know the passwords they used), with the current defaults kept as fallback.
- **Testing the mechanism itself** — one kernel per process is a hard constraint, so kwik's suite gains a second pytest session: `tests_custom_user/` (repo root, outside `testpaths` — the main suite must never collect it) with its own conftest that constructs `Kernel(user_model=CustomTestUser, schemas=...)` (one extra column, e.g. `nickname`) before fixtures run. CI runs it as a separate `pytest tests_custom_user` invocation. Everything under `tests/` proper runs against `DefaultUser`. `_reset_for_testing()` is used only by registry unit tests that never map a model.
- **Typing contract** — kwik has no type checker today (ruff only), so the first-class-typing guarantee gets its own enforcement: `tests_custom_user/test_typing_contract.py` uses `typing.assert_type` to pin `kernel.get_current_user` → `CustomTestUser`, `kernel.crud_users.get(...)` → `CustomTestUser`, `kernel.get_user_context` → `Context[CustomTestUser]`, and CI runs pyright scoped to that file. This is deliberately narrow — a full-repo type-check rollout is out of scope.

### 10. Error handling

All at kernel construction, all `RuntimeError`/`TypeError` with actionable messages:

- Second kernel in the same process (including after the default materialized): "a Kernel is already active; construct yours before importing kwik routers or running the app".
- `user_model` not a subclass of both `Base` and `UserMixin`.
- `__tablename__ != "users"`.
- Missing required mapped columns (`{id, name, surname, email, hashed_password, is_active}`) via SQLAlchemy `inspect()` — safety net for mixin misuse.
- `schemas` provided but incomplete (dataclass enforces all three fields; each must be a `BaseModel` subclass; `profile` must have `from_attributes` enabled).

## Migration Guide Outline (shipped in handbook; executed as teban#266)

1. Define `TebanUser(Base, UserMixin)` with `__tablename__ = "users"`, adding `company`/`external` and the relationships currently on `Resource`.
2. Create `teban/kernel.py` with the `Kernel`, schemas, and typed aliases (`CurrentUser`, `UserContext`).
3. One Alembic migration: add new columns to `users`; rewrite every `resources.id` FK to reference `users.id` (data-migrate via `resources.id → resources.user_id`); drop `resources`.
4. Delete the `Resource` model, its hybrid proxies, `current_resource` dependency, and dual-entity CRUD coordination; replace with `CurrentUser`/direct fields.
5. Swap router assembly to `kernel.create_api_router(...)` + teban routers; update imports that referenced removed kwik singletons (`crud_users` → `kernel.crud_users`).
6. Update seeding to call `kwik.seeding.create_first_superuser(...)`.

## Files Changed (kwik)

| File | Change |
|---|---|
| `kernel.py` | NEW — `Kernel[UserT]`, `UserSchemas`, internal slot, `get_kernel()`, `_reset_for_testing()` |
| `seeding.py` | NEW — `create_first_superuser` battery |
| `models/user_mixin.py` | NEW — auth `UserMixin` (pure mixin) |
| `models/default_user.py` | NEW — `DefaultUser`, lazily imported only |
| `models/user.py` | Concrete `User` deleted; `Role.users` target via callable |
| `models/mixins.py` | `UserMixin` → `UserTrackingMixin` rename |
| `models/api_key.py` | `ApiKey.user` target via callable |
| `models/__init__.py` | Export mixins; no `User`/`DefaultUser` export |
| `__init__.py` | Export `Kernel`, `UserSchemas`, `UserMixin`, default aliases; drop `api_router` |
| `__main__.py` | Default kernel's `create_api_router()` |
| `crud/autocrud.py` | Optional explicit `model=` in `__init__`; relaxed audit-ctx validation |
| `crud/users.py` | `CRUDUsers[UserT]`; `self.model` everywhere; `model_dump()` create; singleton removed |
| `crud/roles.py` | User queries via `get_kernel().user_model` |
| `crud/context.py` | `Context[U: UserMixin \| None]`; aliases re-pointed |
| `dependencies/users.py`, `context.py`, `api_key.py`, `permissions.py` | Resolve via `get_kernel()`; `UserMixin` typing |
| `security.py` | User lookups via `get_kernel().crud_users` |
| `api/endpoints/users.py`, `login.py`, `roles.py` | Converted to kernel-bound factories (no `from __future__ import annotations`) |
| `api/endpoints/__init__.py`, `api/api.py` | Factory exports; singleton `api_router` deleted |
| `testing/scenario.py`, `testing/fixtures/*`, `testing/client.py` | §9 changes |
| `tests_custom_user/` | NEW — custom-model test session + typing contract (`assert_type`) |
| `.github/workflows/test.yml` | Second pytest invocation (`tests_custom_user`) + scoped pyright step |
| `docs/handbook/` | Quickstart rewrite, extensibility page, migration guide |
| `pyproject.toml`, `CHANGELOG.md` | 2.0.0 |

**Not changed:** `models/base.py`, `schemas/user.py` (stock schemas remain as defaults), `crud/permissions.py`, `settings.py`, `database.py`, `routers.py` (`AuthenticatedRouter`/`ApiKeyRouter` classes), `logging.py`.

## Acceptance Criteria

- A consuming app can declare `class AppUser(Base, UserMixin)` with additional columns and relationships, register it via `Kernel(user_model=AppUser, schemas=...)`, and get a **single `users` table** — no auxiliary table, no proxying.
- `kernel.get_current_user` / `kernel.get_user_context` / `kernel.crud_users` are statically typed against the app's class; the documented one-line `Annotated` aliases give autocompleting, type-checked custom fields in endpoints — enforced by `assert_type` contract tests in `tests_custom_user/` under a pyright CI step scoped to that file.
- kwik's auth (JWT + API key + impersonation + password reset), CRUD, and users/login/roles routers work transparently with the custom model; registered schemas bind to both request bodies and response models.
- Zero-config apps work unchanged in behavior: default kernel materializes `DefaultUser` lazily; stock schemas serve the built-in routers.
- Built-in routers are individually opt-out-able via `create_api_router(...)` flags.
- `kwik.seeding.create_first_superuser` works for both default and custom models (idempotent; `extra_fields` for custom non-null columns) and is what `admin_user` fixture uses.
- Scenario/factories support `extra_fields`, validated through the registered registration schema.
- Kernel misconfiguration (double kernel, wrong tablename, missing columns, bad schemas) fails at construction with actionable errors.
- Full kwik test suite passes for `DefaultUser`; the `tests_custom_user/` session passes for a custom model; lint and format clean.
- Migration guide published in the handbook.

## Out of Scope

- Extensible `Role`/`Permission` models (no demonstrated need; the mechanism could be generalized later).
- Custom user table names (fixed `"users"` keeps every string FK untouched).
- Multiple kernels/user models per process (impossible under shared `Base.metadata`).
- Auto-generating Pydantic schemas from the model.
- Teban's actual migration (teban#266, separate repo and cycle).
- Alembic tooling in kwik (apps own migrations, as today).

## Rollout

- Work on `feature/user-model-extensibility`; PR to `main` per the signed-commit rebase workflow.
- Release as **2.0.0** with a changelog documenting the breaking surface: removed `api_router` singleton and router exports, removed `User` export, removed `crud_users` singleton, `UserMixin` → `UserTrackingMixin` rename, `Context` type-parameter change.
- Teban upgrades in its own #266 cycle using the migration guide.
