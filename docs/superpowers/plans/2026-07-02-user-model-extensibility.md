# kwik 2.0 User Model Extensibility (Typed Kernel) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make kwik's User model replaceable by consuming apps via a typed `Kernel[UserT]` registration object, per the approved spec `docs/superpowers/specs/2026-07-02-user-model-extensibility-design.md`.

**Architecture:** kwik ships a side-effect-free `UserMixin` with the auth-essential columns; apps compose `class AppUser(Base, UserMixin)` (table name fixed to `"users"`) and register it once via `Kernel(user_model=..., schemas=...)`. A minimal internal registry (one process-wide slot) lets kwik internals resolve the active model; a lazily-materialized `DefaultUser` kernel keeps zero-config apps working. Users/login/roles routers become kernel-bound factories so registered Pydantic schemas bind to both request bodies and response models.

**Tech Stack:** Python 3.12+ (PEP 695 generics), FastAPI, SQLAlchemy 2.0 declarative, Pydantic v2, pytest + testcontainers, ruff (ALL), pyright (new, scoped), uv.

## Global Constraints

- Work on branch `feature/user-model-extensibility` in `/Users/davide/Developer/kwik`. All commits signed: `git commit -S`.
- Before every commit: `uv run pytest` green, `uv run ruff check` clean, `uv run ruff format` applied. No skipping.
- Line length 120, 4-space indent, type annotations throughout, ruff `select = ["ALL"]`.
- No magic numbers/constants in tests (triggers ruff).
- **Import rule (load-bearing):** no kwik source module or pytest-plugin module may CALL `get_kernel()` at module import time — only inside function/fixture bodies. `kwik/dependencies/*`, `kwik/security.py`, and `kwik/crud/roles.py` must import `get_kernel` function-locally (module-scope import would hit a partially-initialized `kwik.kernel`). `kwik/kernel.py`, `kwik/seeding.py`, tests, and `__main__.py` may import it at module scope.
- **Annotation rule (load-bearing):** `src/kwik/kernel.py` and the factory-converted `src/kwik/api/endpoints/{users,login,roles}.py` must NOT use `from __future__ import annotations` — kernel-bound schema types in FastAPI signatures must evaluate eagerly (deferred strings can't resolve closure variables). Per-file ruff ignores for `FA100`/`FA102` cover this.
- One user model per process: SQLAlchemy cannot map two classes to `__tablename__ = "users"` in the shared `Base.metadata`, and cannot unmap. Never import `kwik.models.default_user` eagerly from kwik source (only `get_kernel()`'s fallback does).
- Required user columns (kernel validation): `{"id", "name", "surname", "email", "hashed_password", "is_active"}`.

**Plan-level deviations from the spec (sync the spec in Task 12):**
1. Custom-model test session lives at repo root `tests_custom_user/` (NOT `tests/custom_user/`) — `testpaths = ["tests"]` must never collect it into the main (DefaultUser) session.
2. `Kernel.get_maybe_user_context` is dropped (YAGNI — no kwik dependency exposes an optional-user context today).

---

### Task 1: Rename audit-trail `UserMixin` → `UserTrackingMixin`

**Files:**
- Modify: `src/kwik/models/mixins.py`
- Modify: `src/kwik/models/__init__.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `kwik.models.UserTrackingMixin` (audit FK columns), freeing the name `UserMixin` for Task 2. `RecordInfoMixin` composition unchanged.

- [ ] **Step 1: Rename the class in `src/kwik/models/mixins.py`**

Replace the `UserMixin` class and `__all__` (rest of file unchanged):

```python
class UserTrackingMixin:
    """Mixin providing user tracking fields for record creation and modification."""

    @declared_attr
    def creator_user_id(self) -> Mapped[int]:
        """Get reference to the user who created this record."""
        return mapped_column(BigInteger, ForeignKey("users.id"))

    @declared_attr
    def last_modifier_user_id(self) -> Mapped[int | None]:
        """Get reference to the user who last modified this record."""
        return mapped_column(BigInteger, ForeignKey("users.id"))


class RecordInfoMixin(TimeStampsMixin, UserTrackingMixin):
    """Combined mixin providing both timestamps and user tracking functionality."""


__all__ = ["RecordInfoMixin", "TimeStampsMixin", "UserTrackingMixin"]
```

- [ ] **Step 2: Update `src/kwik/models/__init__.py`**

```python
from .mixins import RecordInfoMixin, TimeStampsMixin, UserTrackingMixin
```

and in `__all__` replace `"UserMixin"` with `"UserTrackingMixin"`.

- [ ] **Step 3: Verify no stale references**

Run: `grep -rn "UserMixin" src/ tests/`
Expected: only `UserTrackingMixin` occurrences (in `mixins.py` and `models/__init__.py`). No bare `UserMixin` anywhere yet.

- [ ] **Step 4: Run suite and linters**

Run: `uv run pytest` → all pass. `uv run ruff check` → clean. `uv run ruff format` → no changes (or reformats applied).

- [ ] **Step 5: Commit**

```bash
git add src/kwik/models/mixins.py src/kwik/models/__init__.py
git commit -S -m "refactor: rename audit UserMixin to UserTrackingMixin"
```

---

### Task 2: Extract auth `UserMixin`; recompose `User(Base, UserMixin)`

**Files:**
- Create: `src/kwik/models/user_mixin.py`
- Modify: `src/kwik/models/user.py` (reorder: Role/UserRole/Permission/RolePermission first, `User` last and recomposed)
- Modify: `src/kwik/models/__init__.py`

**Interfaces:**
- Consumes: `Base`, `RecordInfoMixin` (Task 1).
- Produces: `kwik.models.user_mixin.UserMixin` — pure mixin (importing it maps nothing) with columns `id, name, surname, email, hashed_password, is_active`, `roles` declared_attr relationship, `permissions` hybrid. Also re-exported as `kwik.models.UserMixin`. The concrete `User` keeps working (suite is the regression gate).

- [ ] **Step 1: Create `src/kwik/models/user_mixin.py`**

```python
"""Auth-essential user mixin for composing concrete user models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

if TYPE_CHECKING:
    from kwik.models.user import Permission, Role


class UserMixin:
    """
    Mixin providing the auth-essential columns and relationships for user models.

    Importing this module maps nothing: concrete user models are composed by the
    consuming application (or kwik's own ``DefaultUser``) as
    ``class MyUser(Base, UserMixin)`` with ``__tablename__ = "users"``.
    """

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    surname: Mapped[str] = mapped_column(String, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @declared_attr
    def roles(self) -> Mapped[list[Role]]:
        """Roles assigned to this user through the users_roles association table."""
        # Deferred import: models.user imports this module at module scope.
        from kwik.models.user import Role, UserRole  # noqa: PLC0415

        return relationship(
            Role,
            secondary="users_roles",
            primaryjoin=lambda: self.id == UserRole.user_id,
            secondaryjoin=lambda: UserRole.role_id == Role.id,
            viewonly=True,
        )

    @hybrid_property
    def permissions(self) -> list[Permission]:
        """Get all permissions for this user through their roles."""
        permissions = []
        for role in self.roles:
            permissions.extend(role.permissions)
        return permissions


__all__ = ["UserMixin"]
```

Note: inside `@declared_attr` methods, `self` IS the mapped class (SQLAlchemy convention, matches `mixins.py` style). The deferred import inside `roles` requires `Role`/`UserRole` to be defined before any `UserMixin`-composed class is created — hence the reorder in Step 2.

- [ ] **Step 2: Rewrite `src/kwik/models/user.py`**

Full new content — `Role`/`UserRole`/`Permission`/`RolePermission` are byte-identical to today except order; `User` is recomposed at the END of the file:

```python
"""Database models for user management and permissions."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from .base import Base
from .mixins import RecordInfoMixin
from .user_mixin import UserMixin


class Role(Base, RecordInfoMixin):
    """Database model for user roles with record tracking."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list[User]] = relationship(
        "User",
        secondary="users_roles",
        primaryjoin="Role.id==UserRole.role_id",
        secondaryjoin="UserRole.user_id==User.id",
        viewonly=True,
    )

    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="roles_permissions",
        viewonly=True,
    )


class UserRole(Base, RecordInfoMixin):
    """Database model for user-role associations with record tracking."""

    __tablename__ = "users_roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)


# Deferred column_property: must be defined after UserRole to avoid forward reference.
Role.user_count = column_property(
    select(func.count(UserRole.id)).where(UserRole.role_id == Role.id).correlate_except(UserRole).scalar_subquery()
)


class Permission(Base, RecordInfoMixin):
    """Database model for system permissions with record tracking."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="roles_permissions",
        viewonly=True,
    )


class RolePermission(Base, RecordInfoMixin):
    """Database model for role-permission associations with record tracking."""

    __tablename__ = "roles_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), nullable=False)


class User(Base, UserMixin):
    """Database model for user accounts with authentication and authorization."""

    __tablename__ = "users"


__all__ = ["Permission", "Role", "RolePermission", "User", "UserRole"]
```

- [ ] **Step 3: Export `UserMixin` from `src/kwik/models/__init__.py`**

Add `from .user_mixin import UserMixin` and `"UserMixin"` to `__all__` (keep everything else, including `User`).

- [ ] **Step 4: Run suite to verify parity**

Run: `uv run pytest`
Expected: all pass — role/permission traversal tests (`tests/crud/test_crud_users.py`, `tests/api/*`) prove the mixin-provided `roles`/`permissions` behave identically.

- [ ] **Step 5: Lint, format, commit**

```bash
uv run ruff check && uv run ruff format
git add src/kwik/models/user_mixin.py src/kwik/models/user.py src/kwik/models/__init__.py
git commit -S -m "feat: extract auth UserMixin; compose User from Base + UserMixin"
```

---

### Task 3: AutoCRUD explicit `model=` + generalized Context

**Files:**
- Modify: `src/kwik/crud/autocrud.py`
- Modify: `src/kwik/crud/context.py`
- Create: `tests/crud/test_autocrud_explicit_model.py`
- Modify (assertion messages only, if matched): `tests/crud/test_autocrud_validation.py`

**Interfaces:**
- Consumes: `UserMixin` (Task 2).
- Produces: `AutoCRUD.__init__(self, *, model: type[ModelType] | None = None)` — explicit model bypasses generic inference. `Context[U: UserMixin | None]` (bound, not constrained) so `Context[AppUser]` is legal; aliases `UserCtx = Context[UserMixin]`, `MaybeUserCtx = Context[UserMixin | None]`, `NoUserCtx = Context[None]`. Audit validation accepts any Context whose user type excludes `None`.

- [ ] **Step 1: Rewrite `src/kwik/crud/context.py`**

```python
"""
CRUD context module for database session and user management.

This module provides context classes for passing database sessions and user
information through the CRUD layer of the application. It includes:

- Context: Generic context class for holding session and user data
- UserCtx: Type alias for authenticated user context
- MaybeUserCtx: Type alias for optionally authenticated user context
- NoUserCtx: Type alias for unauthenticated context
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from kwik.models.user_mixin import UserMixin

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(slots=True, frozen=True)
class Context[U: UserMixin | None]:
    """
    A context object that holds database session and user information meant to be used at the CRUD layer level.

    This generic class provides a way to pass both database session and user
    context through the application. The user type parameter is bounded by
    ``UserMixin | None`` so consuming applications can parameterize it with
    their own concrete user model (e.g. ``Context[AppUser]``).

    Attributes
    ----------
    session : Session
        The SQLAlchemy database session.
    user : U
        The user object; ``None`` for unauthenticated contexts.

    """

    session: Session
    user: U


type UserCtx = Context[UserMixin]
type MaybeUserCtx = Context[UserMixin | None]
type NoUserCtx = Context[None]
```

Note: `UserMixin` is imported at RUNTIME (side-effect-free module) — the `type` alias values are evaluated lazily but AT RUNTIME by the validation helper below, so a `TYPE_CHECKING` import would `NameError`.

- [ ] **Step 2: Modify `src/kwik/crud/autocrud.py`**

Change the imports (add `TypeVar`, drop `UserCtx`):

```python
from typing import TYPE_CHECKING, ClassVar, TypeVar, get_args
...
from .context import Context
```

Add a module-level helper after `_sort_query`:

```python
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
```

Replace `AutoCRUD.__init__` with:

```python
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
```

Everything below `__init__` (all CRUD methods) is unchanged.

- [ ] **Step 3: Write the failing tests — `tests/crud/test_autocrud_explicit_model.py`**

```python
"""Tests for explicit model passing and audit-context validation in AutoCRUD."""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column

from kwik.crud import AutoCRUD, Context, MaybeUserCtx, NoUserCtx, UserCtx
from kwik.models import Base, RecordInfoMixin, UserMixin


class _Widget(Base):
    __tablename__ = "autocrud_explicit_widgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)


class _AuditedWidget(Base, RecordInfoMixin):
    __tablename__ = "autocrud_explicit_audited_widgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)


class _WidgetPayload(BaseModel):
    label: str


class _AppUser(UserMixin):
    """Structural stand-in for an app-defined user model (deliberately not mapped)."""


type _AppCtx = Context[_AppUser]


class _GenericWidgetCRUD[ModelT: Base](AutoCRUD[NoUserCtx, ModelT, _WidgetPayload, _WidgetPayload, int]):
    """Generic-over-model CRUD, mirroring the kernel-owned users CRUD shape."""


class TestExplicitModel:
    def test_explicit_model_bypasses_generic_inference(self) -> None:
        crud = _GenericWidgetCRUD(model=_Widget)
        assert crud.model is _Widget

    def test_generic_type_parameter_without_explicit_model_raises(self) -> None:
        with pytest.raises(TypeError, match="pass the concrete model explicitly"):
            _GenericWidgetCRUD()


class TestAuditContextValidation:
    def test_user_ctx_alias_is_accepted(self) -> None:
        class _AuditedCRUD(AutoCRUD[UserCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        assert _AuditedCRUD().model is _AuditedWidget

    def test_app_defined_context_alias_is_accepted(self) -> None:
        class _AppAuditedCRUD(AutoCRUD[_AppCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        assert _AppAuditedCRUD().model is _AuditedWidget

    def test_optional_user_context_is_rejected(self) -> None:
        class _MaybeAuditedCRUD(AutoCRUD[MaybeUserCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        with pytest.raises(ValueError, match="non-optional user"):
            _MaybeAuditedCRUD()

    def test_no_user_context_is_rejected(self) -> None:
        class _NoUserAuditedCRUD(AutoCRUD[NoUserCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        with pytest.raises(ValueError, match="non-optional user"):
            _NoUserAuditedCRUD()
```

- [ ] **Step 4: Run the new tests**

Run: `uv run pytest tests/crud/test_autocrud_explicit_model.py -n 0 -v`
Expected: PASS (implementation from Step 2 is already in place; if you wrote the test first, it fails with `TypeError: __init__() got an unexpected keyword argument 'model'` — either order is fine, but both steps must end green).

- [ ] **Step 5: Reconcile existing validation tests**

Run: `grep -n "UserCtx\|match=" tests/crud/test_autocrud_validation.py`
If any `pytest.raises(..., match=...)` matches the OLD message text (`"Use UserCtx as the first generic parameter"`), update the match string to `"non-optional user"`. Behavior (raise vs no-raise) is unchanged for all existing cases.

- [ ] **Step 6: Full suite, lint, commit**

```bash
uv run pytest && uv run ruff check && uv run ruff format
git add src/kwik/crud/autocrud.py src/kwik/crud/context.py tests/crud/
git commit -S -m "feat: AutoCRUD explicit model + Context bounded by UserMixin"
```

---

### Task 4: `CRUDUsers[UserT]` — generic users CRUD with `model_dump()` create

**Files:**
- Modify: `src/kwik/crud/users.py` (full rewrite below)
- Modify: `src/kwik/crud/__init__.py`

**Interfaces:**
- Consumes: `AutoCRUD(model=...)` (Task 3), `UserMixin` (Task 2).
- Produces: `kwik.crud.CRUDUsers[UserT: UserMixin]` — constructed as `CRUDUsers(model=SomeUserModel)`. All methods keyword-only, same names/signatures as today except: `create(*, obj_in: BaseModel, context)` (duck-typed payload with a `password` field), `is_active/has_permissions/has_roles/get_permissions/get_roles` accept `user: UserMixin`. TRANSITIONAL module singleton `crud_users = CRUDUsers(model=User)` keeps every current import site working (deleted in Task 9).

- [ ] **Step 1: Rewrite `src/kwik/crud/users.py`**

```python
"""CRUD operations for users database entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel
from sqlalchemy import select

from kwik.exceptions import AuthenticationFailedError, InactiveUserError, UserNotFoundError
from kwik.models import User
from kwik.models.user_mixin import UserMixin
from kwik.security import get_password_hash, verify_password

from .autocrud import AutoCRUD
from .context import MaybeUserCtx

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kwik.models import Permission, Role
    from kwik.schemas import UserPasswordChange


class CRUDUsers[UserT: UserMixin](AutoCRUD[MaybeUserCtx, UserT, BaseModel, BaseModel, int]):
    """
    CRUD operations for user models with authentication and authorization support.

    Generic over the concrete user model; the kernel constructs it with the
    registered model: ``CRUDUsers(model=user_model)``.
    """

    # Expose only safe/public fields for list filtering/sorting
    list_allowed_fields: ClassVar[set[str]] = {"id", "name", "surname", "email", "is_active"}

    def get_by_email(self, *, email: str, context: MaybeUserCtx) -> UserT | None:
        """Get user by email address."""
        stmt = select(self.model).where(self.model.email == email)
        return context.session.execute(stmt).scalar_one_or_none()

    def create(self, *, obj_in: BaseModel, context: MaybeUserCtx) -> UserT:
        """
        Create new user with hashed password.

        Dumps the full registration payload so custom fields on extended user
        models flow into the model constructor; the plaintext ``password`` field
        is replaced by ``hashed_password``.
        """
        data = obj_in.model_dump()
        password = data.pop("password")
        db_obj = self.model(**data, hashed_password=get_password_hash(password))
        context.session.add(db_obj)
        context.session.flush()
        context.session.refresh(db_obj)

        return db_obj

    def create_if_not_exist(
        self,
        *,
        obj_in: BaseModel,
        context: MaybeUserCtx,
        filters: dict[str, str],
        raise_on_error: bool = False,  # noqa: ARG002
    ) -> UserT:
        """Create user if it doesn't exist based on filters, otherwise return existing user."""
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)

        obj_db = context.session.execute(stmt).scalar_one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in, context=context)
        return obj_db

    def authenticate(self, *, email: str, password: str, context: MaybeUserCtx) -> UserT:
        """Authenticate a user with email and password."""
        user = self.get_by_email(email=email, context=context)

        # Check if the user exists and the password is correct
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationFailedError

        return user

    def change_password(self, *, user_id: int, obj_in: UserPasswordChange, context: MaybeUserCtx) -> UserT:
        """Change user password after validating old password."""
        user_db = self.get(entity_id=user_id, context=context)

        if not user_db:
            raise UserNotFoundError

        if not self.authenticate(email=user_db.email, password=obj_in.old_password, context=context):
            raise AuthenticationFailedError

        hashed_password = get_password_hash(obj_in.new_password)
        user_db.hashed_password = hashed_password

        return user_db

    def reset_password(self, *, email: str, password: str, context: MaybeUserCtx) -> UserT:
        """Reset user password by email."""
        user_db = self.get_by_email(email=email, context=context)

        if user_db is None:
            raise UserNotFoundError

        self.is_active(user_db)

        hashed_password = get_password_hash(password)
        user_db.hashed_password = hashed_password
        context.session.add(user_db)
        context.session.flush()

        return user_db

    def admin_reset_password(self, *, user_id: int, password: str, context: MaybeUserCtx) -> UserT:
        """Reset user password by user ID (admin operation, no old password required)."""
        user_db = self.get(entity_id=user_id, context=context)

        if user_db is None:
            raise UserNotFoundError

        self.is_active(user_db)

        user_db.hashed_password = get_password_hash(password)
        context.session.add(user_db)
        context.session.flush()

        return user_db

    @staticmethod
    def is_active(user: UserMixin) -> UserMixin:
        """Check if user is active, raise exception if not."""
        if not user.is_active:
            raise InactiveUserError
        return user

    def has_permissions(self, *, user: UserMixin, permissions: Sequence[str]) -> bool:
        """Check if the user has all the permissions provided."""
        user_permission_names = {permission.name for permission in user.permissions}
        return all(permission in user_permission_names for permission in permissions)

    def has_roles(self, *, user: UserMixin, roles: Sequence[str]) -> bool:
        """Check if the user has all the roles provided."""
        user_role_names = {role.name for role in user.roles}
        return all(role in user_role_names for role in roles)

    def get_permissions(self, *, user: UserMixin) -> list[Permission]:
        """Get all permissions given to the user."""
        return user.permissions

    def get_roles(self, *, user: UserMixin) -> list[Role]:
        """Get all roles associated to the user."""
        return user.roles


# TRANSITIONAL singleton (deleted in the router-factory task): keeps existing import
# sites working while internals migrate to get_kernel().crud_users.
crud_users = CRUDUsers(model=User)

__all__ = ["CRUDUsers", "crud_users"]
```

- [ ] **Step 2: Export the class from `src/kwik/crud/__init__.py`**

```python
from .users import CRUDUsers, crud_users
```

and add `"CRUDUsers"` to `__all__` (keep `"crud_users"` for now).

- [ ] **Step 3: Run suite, lint, commit**

Run: `uv run pytest` → all pass (behavioral parity: the `model_dump()` create path produces identical rows for the stock `UserRegistration`; `tests/crud/test_crud_users.py` and the API tests are the gate).

```bash
uv run ruff check && uv run ruff format
git add src/kwik/crud/users.py src/kwik/crud/__init__.py
git commit -S -m "feat: generic CRUDUsers with explicit model and model_dump create"
```

---

### Task 5: `kwik/kernel.py` — Kernel, UserSchemas, slot, get_kernel

**Files:**
- Create: `src/kwik/kernel.py`
- Create: `tests/test_kernel.py`
- Modify: `pyproject.toml` (ruff per-file-ignores)

**Interfaces:**
- Consumes: `CRUDUsers` (Task 4), `UserMixin`, `Base`, stock user schemas.
- Produces: `kwik.kernel.Kernel[UserT: UserMixin]` with attributes `user_model: type[UserT]`, `schemas: UserSchemas`, `crud_users: CRUDUsers[UserT]`; `kwik.kernel.UserSchemas(profile, registration, update)` frozen dataclass; `kwik.kernel.get_kernel() -> Kernel[UserMixin]` (lazy `DefaultUser` fallback — the fallback import target is created in Task 6); `kwik.kernel._reset_for_testing()`. Constructor validates model and schemas BEFORE claiming the slot.

- [ ] **Step 1: Create `src/kwik/kernel.py`**

```python
"""
Typed kernel: the single registration point for the application's user model and schemas.

A consuming application constructs exactly one ``Kernel`` — before importing kwik
routers or running the app. kwik internals resolve the active kernel via
``get_kernel()``, which materializes a default kernel wired to ``DefaultUser``
for zero-config applications.

This module must not use ``from __future__ import annotations``: FastAPI-facing
signatures added here must evaluate eagerly.
"""

from dataclasses import dataclass
from typing import Final

from pydantic import BaseModel
from sqlalchemy import inspect

from kwik.crud.users import CRUDUsers
from kwik.models.base import Base
from kwik.models.user_mixin import UserMixin
from kwik.schemas import UserProfile, UserProfileUpdate, UserRegistration

_REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset(
    {"id", "name", "surname", "email", "hashed_password", "is_active"}
)


@dataclass(frozen=True)
class UserSchemas:
    """Bundle of Pydantic schema types bound to kwik's user endpoints."""

    profile: type[BaseModel]
    registration: type[BaseModel]
    update: type[BaseModel]


def _validate_user_model(user_model: type) -> None:
    """Fail fast with actionable messages; runs BEFORE the slot is claimed."""
    if not (isinstance(user_model, type) and issubclass(user_model, Base)):
        msg = f"{user_model!r} must be a SQLAlchemy model (a subclass of kwik.models.Base)"
        raise TypeError(msg)
    if not issubclass(user_model, UserMixin):
        msg = f"{user_model.__name__} must subclass kwik.models.UserMixin to provide the auth-essential columns"
        raise TypeError(msg)
    if user_model.__tablename__ != "users":
        msg = (
            f"{user_model.__name__} must map __tablename__ = 'users' (got {user_model.__tablename__!r}); "
            f"kwik's foreign keys reference the 'users' table"
        )
        raise TypeError(msg)
    mapped_columns = set(inspect(user_model).columns.keys())
    missing = _REQUIRED_COLUMNS - mapped_columns
    if missing:
        msg = f"{user_model.__name__} is missing required mapped columns: {sorted(missing)}"
        raise TypeError(msg)


def _validate_schemas(schemas: UserSchemas) -> None:
    for field_name in ("profile", "registration", "update"):
        schema = getattr(schemas, field_name)
        if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
            msg = f"UserSchemas.{field_name} must be a Pydantic BaseModel subclass (got {schema!r})"
            raise TypeError(msg)
    if not schemas.profile.model_config.get("from_attributes", False):
        msg = "UserSchemas.profile must enable model_config['from_attributes'] to serialize ORM objects"
        raise TypeError(msg)


class Kernel[UserT: UserMixin]:
    """Process-wide registration of the application's user model and schemas."""

    user_model: type[UserT]
    schemas: UserSchemas
    crud_users: CRUDUsers[UserT]

    def __init__(self, *, user_model: type[UserT], schemas: UserSchemas | None = None) -> None:
        """Validate the model and schemas, then claim the process-wide kernel slot."""
        _validate_user_model(user_model)
        if schemas is not None:
            _validate_schemas(schemas)
        _claim_slot(self)
        self.user_model = user_model
        self.schemas = (
            schemas
            if schemas is not None
            else UserSchemas(profile=UserProfile, registration=UserRegistration, update=UserProfileUpdate)
        )
        self.crud_users = CRUDUsers(model=user_model)


_active_kernel: Kernel[UserMixin] | None = None


def _claim_slot(kernel: Kernel[UserMixin]) -> None:
    global _active_kernel  # noqa: PLW0603 — deliberate single process-wide slot
    if _active_kernel is not None:
        msg = (
            "A kwik Kernel is already active in this process. Construct your Kernel exactly once, "
            "before importing kwik routers or running the app (the default kernel materializes on first use)."
        )
        raise RuntimeError(msg)
    _active_kernel = kernel


def get_kernel() -> Kernel[UserMixin]:
    """Return the active kernel, materializing the DefaultUser kernel when none was registered."""
    kernel = _active_kernel
    if kernel is None:
        # Lazy import: DefaultUser is mapped only when actually needed, so a custom
        # user model never collides with it in Base.metadata.
        from kwik.models.default_user import DefaultUser  # noqa: PLC0415

        kernel = Kernel(user_model=DefaultUser)
    return kernel


def _reset_for_testing() -> None:
    """Clear the kernel slot. Test-only; models already mapped by the outgoing kernel stay mapped."""
    global _active_kernel  # noqa: PLW0603
    _active_kernel = None


__all__ = ["Kernel", "UserSchemas", "get_kernel"]
```

- [ ] **Step 2: Add ruff per-file-ignores in `pyproject.toml`**

Under `[tool.ruff.lint.per-file-ignores]` add:

```toml
"src/kwik/kernel.py" = ["FA100", "FA102"]
```

- [ ] **Step 3: Write the tests — `tests/test_kernel.py`**

Slot manipulation always goes through `monkeypatch` (auto-restored), so these tests are order-independent and safe alongside the session kernel that fixtures will own from Task 6 on. `User` here is the concrete model (becomes the `DefaultUser` alias in Task 6, rewritten in Task 10).

```python
"""Tests for the kwik Kernel registry and validation."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

import kwik.kernel
from kwik.kernel import Kernel, UserSchemas, get_kernel
from kwik.models import Base, Role, User, UserMixin
from kwik.schemas import UserProfile, UserProfileUpdate, UserRegistration


class _WrongTableUser(Base, UserMixin):
    """Valid composition but wrong table name — must be rejected."""

    __tablename__ = "kernel_test_users"


class _PlainProfile(BaseModel):
    """Profile schema WITHOUT from_attributes — must be rejected."""

    id: int


@pytest.fixture
def clean_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Detach the process-wide kernel slot for the duration of one test."""
    monkeypatch.setattr(kwik.kernel, "_active_kernel", None)


class TestKernelValidation:
    """All validation failures raise BEFORE the slot is claimed — no fixture needed."""

    def test_rejects_non_model(self) -> None:
        class _NotAModel:
            pass

        with pytest.raises(TypeError, match="SQLAlchemy model"):
            Kernel(user_model=_NotAModel)

    def test_rejects_model_without_user_mixin(self) -> None:
        with pytest.raises(TypeError, match="UserMixin"):
            Kernel(user_model=Role)

    def test_rejects_wrong_tablename(self) -> None:
        with pytest.raises(TypeError, match="__tablename__"):
            Kernel(user_model=_WrongTableUser)

    def test_rejects_non_schema_in_bundle(self) -> None:
        class _NotASchema:
            pass

        bundle = UserSchemas(profile=_NotASchema, registration=UserRegistration, update=UserProfileUpdate)
        with pytest.raises(TypeError, match="BaseModel subclass"):
            Kernel(user_model=User, schemas=bundle)

    def test_rejects_profile_without_from_attributes(self) -> None:
        bundle = UserSchemas(profile=_PlainProfile, registration=UserRegistration, update=UserProfileUpdate)
        with pytest.raises(TypeError, match="from_attributes"):
            Kernel(user_model=User, schemas=bundle)


class TestKernelSlot:
    def test_claims_slot_and_get_kernel_returns_it(self, clean_slot: None) -> None:
        kernel = Kernel(user_model=User)
        assert get_kernel() is kernel
        assert kernel.user_model is User
        assert kernel.crud_users.model is User

    def test_double_registration_raises(self, clean_slot: None) -> None:
        Kernel(user_model=User)
        with pytest.raises(RuntimeError, match="already active"):
            Kernel(user_model=User)

    def test_default_schemas_applied_when_not_provided(self, clean_slot: None) -> None:
        kernel = Kernel(user_model=User)
        expected = UserSchemas(profile=UserProfile, registration=UserRegistration, update=UserProfileUpdate)
        assert kernel.schemas == expected

    def test_reset_for_testing_clears_slot(self, clean_slot: None) -> None:
        Kernel(user_model=User)
        kwik.kernel._reset_for_testing()
        assert kwik.kernel._active_kernel is None
```

- [ ] **Step 4: Run the new tests**

Run: `uv run pytest tests/test_kernel.py -n 0 -v`
Expected: PASS. (`get_kernel()`'s DefaultUser fallback branch stays unexercised until Task 6 — `kwik/models/default_user.py` does not exist yet and nothing calls the fallback.)

- [ ] **Step 5: Full suite, lint, commit**

```bash
uv run pytest && uv run ruff check && uv run ruff format
git add src/kwik/kernel.py tests/test_kernel.py pyproject.toml
git commit -S -m "feat: add Kernel registry with validation and lazy default"
```

---

### Task 6: The model switch — `DefaultUser`, dynamic relationship targets, transitional alias

**Files:**
- Create: `src/kwik/models/default_user.py`
- Modify: `src/kwik/models/user.py` (delete `User`, dynamic `Role.users`)
- Modify: `src/kwik/models/api_key.py` (dynamic `ApiKey.user`)
- Modify: `src/kwik/models/__init__.py` (TRANSITIONAL `User = DefaultUser` alias)
- Modify: `tests/test_kernel.py` (add default-kernel test)

**Interfaces:**
- Consumes: `UserMixin`, `get_kernel()` (Task 5).
- Produces: `kwik.models.default_user.DefaultUser(Base, UserMixin)`; `Role.users` and `ApiKey.user` resolve their target class at mapper-configuration time via the kernel. `from kwik.models import User` keeps working via a TRANSITIONAL eager alias to `DefaultUser` (removed in Task 10) — so `crud/users.py`'s temp singleton and all test imports stay untouched in this task.

- [ ] **Step 1: Create `src/kwik/models/default_user.py`**

```python
"""
Default concrete user model for applications that do not register a custom one.

This module is imported ONLY by ``kwik.kernel.get_kernel()``'s fallback path —
never eagerly from kwik source: importing it maps the ``users`` table, which
must not happen when a consuming application composes its own user model.
"""

from kwik.models.base import Base
from kwik.models.user_mixin import UserMixin


class DefaultUser(Base, UserMixin):
    """Default user model for zero-configuration kwik applications."""

    __tablename__ = "users"


__all__ = ["DefaultUser"]
```

- [ ] **Step 2: Modify `src/kwik/models/user.py`**

Delete the `class User(...)` block at the end of the file, and change `Role`:

Add after the imports (and add `from .user_mixin import UserMixin` as a RUNTIME import — it already exists from Task 2):

```python
def _user_model() -> type[UserMixin]:
    """Resolve the registered user model; deferred until mapper configuration."""
    from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred to avoid circular import

    return get_kernel().user_model
```

Replace `Role.users` with an unannotated assignment (annotation omitted deliberately: the target class is dynamic, and SQLAlchemy must take it from the relationship argument, not from a `Mapped[...]` annotation):

```python
    users = relationship(
        _user_model,
        secondary="users_roles",
        primaryjoin=lambda: Role.id == UserRole.role_id,
        secondaryjoin=lambda: UserRole.user_id == _user_model().id,
        viewonly=True,
    )
```

Update `__all__ = ["Permission", "Role", "RolePermission", "UserRole"]`.

- [ ] **Step 3: Modify `src/kwik/models/api_key.py`**

Remove the `if TYPE_CHECKING: from .user import User` block. Add after the imports:

```python
def _user_model() -> type:
    """Resolve the registered user model; deferred until mapper configuration."""
    from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred to avoid circular import

    return get_kernel().user_model
```

Replace the `user` relationship line with an unannotated assignment:

```python
    user = relationship(_user_model, lazy="joined")
```

Also update the class docstring's `user:` attribute line to say "Relationship to the registered user model."

- [ ] **Step 4: Modify `src/kwik/models/__init__.py`**

```python
"""
Data models package for kwik framework.

This package contains SQLAlchemy models for user management
functionality within the kwik web framework.
"""

from .api_key import ApiKey
from .base import Base

# TRANSITIONAL (removed before release): keeps `from kwik.models import User` working
# during the incremental 2.0 migration. Eagerly maps DefaultUser.
from .default_user import DefaultUser as User
from .mixins import RecordInfoMixin, TimeStampsMixin, UserTrackingMixin
from .user import Permission, Role, RolePermission, UserRole
from .user_mixin import UserMixin

__all__ = [
    "ApiKey",
    "Base",
    "Permission",
    "RecordInfoMixin",
    "Role",
    "RolePermission",
    "TimeStampsMixin",
    "User",
    "UserMixin",
    "UserRole",
    "UserTrackingMixin",
]
```

- [ ] **Step 5: Add the default-kernel test to `tests/test_kernel.py`**

Append inside `TestKernelSlot`:

```python
    def test_default_kernel_materializes_default_user(self, clean_slot: None) -> None:
        from kwik.models.default_user import DefaultUser

        kernel = get_kernel()
        assert kernel.user_model is DefaultUser
        assert kwik.kernel._active_kernel is kernel
```

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: all pass. This exercises the whole switch: `Role.users` / `ApiKey.user` resolve through the kernel at first mapper configuration (triggered by the first flush in fixtures), the default kernel claims the slot, and the transitional alias keeps `crud_users = CRUDUsers(model=User)` operating on `DefaultUser`.

- [ ] **Step 7: Lint, format, commit**

```bash
uv run ruff check && uv run ruff format
git add src/kwik/models/ tests/test_kernel.py
git commit -S -m "feat!: replace concrete User with DefaultUser resolved via kernel"
```

---

### Task 7: Internals resolve the user model through the kernel

**Files:**
- Modify: `src/kwik/security.py`
- Modify: `src/kwik/dependencies/users.py`
- Modify: `src/kwik/dependencies/api_key.py`
- Modify: `src/kwik/dependencies/permissions.py`
- Modify: `src/kwik/crud/roles.py`

**Interfaces:**
- Consumes: `get_kernel()` (Task 5). Endpoints keep using the transitional `crud_users` singleton until Task 9 — identical behavior, since both operate on the same model class.
- Produces: `current_user`/`resolved_user` typed `Annotated[UserMixin, ...]`; `security.authenticate_from_token -> UserMixin`; `CRUDRole.get_users_with/get_users_without -> list[UserMixin]`. All user lookups in these five modules go through `get_kernel()` (function-local imports, per the Global Constraints import rule).

- [ ] **Step 1: Modify `src/kwik/security.py`**

- In the `TYPE_CHECKING` block: replace `from kwik.models import User` with `from kwik.models.user_mixin import UserMixin`.
- In `verify_password_reset_token`, replace the local import and lookup:

```python
    # Local import to avoid circular dependency: crud.users imports security for hashing
    from kwik.kernel import get_kernel  # noqa: PLC0415

    ...
    user = get_kernel().crud_users.get_by_email(email=email, context=context)
```

- In `authenticate_from_token`: change the return annotation to `-> UserMixin`, update the docstring line "The authenticated User ORM object." → "The authenticated user ORM object (instance of the registered user model).", and replace the local imports/lookup:

```python
    # Local imports to avoid circular dependency: crud.users imports security for hashing
    from kwik.crud.context import Context  # noqa: PLC0415
    from kwik.exceptions import AccessDeniedError  # noqa: PLC0415
    from kwik.kernel import get_kernel  # noqa: PLC0415

    payload = decode_token(token=token, settings=settings)
    if payload.sub is None:
        raise AccessDeniedError
    context = Context(session=session, user=None)
    user = get_kernel().crud_users.get(entity_id=int(payload.sub), context=context)
    if user is None:
        raise AccessDeniedError
    return user
```

- [ ] **Step 2: Modify `src/kwik/dependencies/users.py`**

- Remove `from kwik.crud import crud_users` and `from kwik.models import User`.
- Add runtime import `from kwik.models.user_mixin import UserMixin` (runtime, not TYPE_CHECKING: the `Annotated[...]` aliases at the bottom are runtime expressions).
- In `_get_current_user`, replace the lookup:

```python
    from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred: kernel imports kwik.dependencies

    context = Context(session=session, user=None)
    user = get_kernel().crud_users.get(entity_id=token.sub, context=context)
```

- Same replacement in the JWT path of `_resolve_current_user`.
- Change both return annotations `-> User` to `-> UserMixin`.
- Replace the aliases:

```python
current_user = Annotated[UserMixin, Depends(_get_current_user)]
resolved_user = Annotated[UserMixin, Depends(_resolve_current_user)]
```

- [ ] **Step 3: Modify `src/kwik/dependencies/api_key.py`**

Remove `from kwik.models.user import User`. In `_verify_api_key`, replace the user lookup:

```python
    from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred: kernel imports kwik.dependencies

    user = session.get(get_kernel().user_model, api_key.user_id)
```

- [ ] **Step 4: Modify `src/kwik/dependencies/permissions.py`**

Remove `from kwik.crud import crud_users`. Inside `check_permissions`:

```python
    def check_permissions(user: resolved_user) -> None:
        from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred: kernel imports kwik.dependencies

        if not get_kernel().crud_users.has_permissions(user=user, permissions=permissions):
            raise AccessDeniedError
```

- [ ] **Step 5: Modify `src/kwik/crud/roles.py`**

- Change the models import to `from kwik.models import Permission, Role, RolePermission, UserRole` and add `from kwik.models.user_mixin import UserMixin` (runtime import — used in signatures resolved at runtime by nothing, but keep it runtime for consistency with `context.py`).
- Add a static helper on `CRUDRole`:

```python
    @staticmethod
    def _user_model() -> type[UserMixin]:
        """Resolve the registered user model for direct user queries."""
        from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred to avoid circular import

        return get_kernel().user_model
```

- `get_users_with(self, *, role: Role) -> list[UserMixin]` (annotation change only).
- Rewrite `get_users_without`:

```python
    def get_users_without(self, *, role_id: int, context: UserCtx) -> list[UserMixin]:
        """Get all users not involved in the given role, including users with no role."""
        user_model = self._user_model()
        stmt = (
            select(user_model)
            .outerjoin(UserRole, user_model.id == UserRole.user_id)
            .filter(or_(UserRole.role_id.is_(None), UserRole.role_id != role_id))
        )
        return list(context.session.execute(stmt).scalars().all())
```

- `assign_user(self, *, role: Role, user: UserMixin, context: UserCtx) -> Role` and `remove_user(self, *, role: Role, user: UserMixin, context: UserCtx) -> Role` (annotation changes only; bodies unchanged).

- [ ] **Step 6: Full suite, lint, commit**

Run: `uv run pytest && uv run ruff check && uv run ruff format`
Expected: all pass — the transitional singleton and the kernel's `crud_users` operate on the same `DefaultUser` model, so behavior is identical.

```bash
git add src/kwik/security.py src/kwik/dependencies/ src/kwik/crud/roles.py
git commit -S -m "refactor: resolve user model via kernel in security, dependencies, roles CRUD"
```

---

### Task 8: Seeding battery + testing-utility upgrades

**Files:**
- Create: `src/kwik/seeding.py`
- Modify: `src/kwik/testing/fixtures/core_fixtures.py`
- Modify: `src/kwik/testing/scenario.py`
- Modify: `src/kwik/testing/fixtures/factories.py`
- Modify: `src/kwik/testing/client.py`
- Create: `tests/test_seeding.py`
- Create: `tests/testing/test_scenario_passwords.py`
- Create: `tests/api/test_client_passwords.py`

**Interfaces:**
- Consumes: `get_kernel()`, `crud_roles`, `crud_permissions`.
- Produces: `kwik.seeding.create_first_superuser(*, session, settings, **extra_fields) -> UserMixin` (idempotent; `ADMIN_ROLE_NAME = "admin"`); `UserSpec.extra_fields: dict[str, object]`; `Scenario.with_user(..., extra_fields=None)`; `ScenarioResult.passwords: dict[str, str]` (email → plaintext password); `user_factory(..., extra_fields=None)`; `IdentityAwareTestClient.register_passwords(passwords: dict[str, str])` checked before the legacy per-email fallbacks.
- CRITICAL: no module in `kwik/testing/` may CALL `get_kernel()` at import time (the fixtures package is loaded as a pytest plugin BEFORE a consuming conftest registers its custom kernel). Calls go inside fixture/method bodies only.

- [ ] **Step 1: Create `src/kwik/seeding.py`**

```python
"""First-superuser seeding battery shared by production apps and kwik's own test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.crud import crud_permissions, crud_roles
from kwik.crud.context import Context
from kwik.kernel import get_kernel
from kwik.schemas import PermissionDefinition, RoleDefinition

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models.user_mixin import UserMixin
    from kwik.settings import BaseKwikSettings

ADMIN_ROLE_NAME = "admin"


def create_first_superuser(*, session: Session, settings: BaseKwikSettings, **extra_fields: object) -> UserMixin:
    """
    Idempotently create the first superuser with the admin role and every permission.

    Creates the user from ``settings.FIRST_SUPERUSER`` / ``FIRST_SUPERUSER_PASSWORD``
    through the kernel's registered registration schema, so custom user models work
    transparently; ``extra_fields`` feeds additional registration fields required by
    custom models (e.g. non-null custom columns).

    Returns the superuser (existing or newly created).
    """
    kernel = get_kernel()
    no_user_context = Context(session=session, user=None)

    existing = kernel.crud_users.get_by_email(email=settings.FIRST_SUPERUSER, context=no_user_context)
    if existing is not None:
        return existing

    registration = kernel.schemas.registration(
        name="admin",
        surname="admin",
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        is_active=True,
        **extra_fields,
    )
    superuser = kernel.crud_users.create(obj_in=registration, context=no_user_context)

    admin_context = Context(session=session, user=superuser)
    admin_role = crud_roles.create_if_not_exist(
        obj_in=RoleDefinition(name=ADMIN_ROLE_NAME, is_active=True),
        context=admin_context,
        filters={"name": ADMIN_ROLE_NAME},
    )
    for permission_name in Permissions:
        permission = crud_permissions.create_if_not_exist(
            obj_in=PermissionDefinition(name=permission_name.value),
            context=admin_context,
            filters={"name": permission_name.value},
        )
        crud_roles.assign_permission(role=admin_role, permission=permission, context=admin_context)
    crud_roles.assign_user(role=admin_role, user=superuser, context=admin_context)

    return superuser


__all__ = ["ADMIN_ROLE_NAME", "create_first_superuser"]
```

- [ ] **Step 2: Modify `src/kwik/testing/fixtures/core_fixtures.py`**

- Imports: remove `crud_users` from the `kwik.crud` import (keep `Context, NoUserCtx, UserCtx`; `crud_permissions`/`crud_roles`/`Permissions`/`PermissionDefinition`/`RoleDefinition`/`UserRegistration` imports become unused — remove them too). Add `from kwik.kernel import get_kernel` and `from kwik.seeding import create_first_superuser`. In `TYPE_CHECKING`, replace `from kwik.models import User` with `from kwik.models.user_mixin import UserMixin`.
- `engine` fixture — map the active user model before `create_all`:

```python
@pytest.fixture(scope="session", autouse=True)
def engine(settings: BaseKwikSettings) -> Generator[Engine, None, None]:
    """Create a database engine and manage schema lifecycle for tests."""
    get_kernel()  # ensure the active user model is mapped before create_all
    engine = create_engine(settings)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
```

- Replace `admin_user` entirely:

```python
@pytest.fixture(scope="session", autouse=True)
def admin_user(settings: BaseKwikSettings, engine: Engine) -> UserMixin:
    """Create a shared admin user via the seeding battery (idempotent)."""
    _session = create_session(engine=engine)
    with session_scope(session=_session, commit=True) as scoped_session:
        user = create_first_superuser(session=scoped_session, settings=settings)
        scoped_session.refresh(user)
        return user
```

- `regular_user`: change annotation to `-> UserMixin` and the body's CRUD call to `get_kernel().crud_users.create_if_not_exist(...)`; the `UserRegistration(...)` payload becomes `get_kernel().schemas.registration(...)` with the same field values.
- `admin_context`: parameter annotation `admin_user: UserMixin`.

- [ ] **Step 3: Modify `src/kwik/testing/scenario.py`**

- Imports: remove `crud_users` from the `kwik.crud` import and remove `UserRegistration` from the schemas import; add `from kwik.kernel import get_kernel`. In `TYPE_CHECKING`, replace `from kwik.models import Permission, Role, User` with `from kwik.models import Permission, Role` plus `from kwik.models.user_mixin import UserMixin`; replace `User` annotations with `UserMixin` throughout the file (`ScenarioResult.users: dict[str, UserMixin]`, `build(..., admin_user: UserMixin | None = None)`).
- `ScenarioResult` gains passwords:

```python
@dataclass
class ScenarioResult:
    """Container for all entities created by a scenario build."""

    users: dict[str, UserMixin] = field(default_factory=dict)
    roles: dict[str, Role] = field(default_factory=dict)
    permissions: dict[str, Permission] = field(default_factory=dict)
    passwords: dict[str, str] = field(default_factory=dict)
    """Plaintext passwords keyed by user email, for IdentityAwareTestClient.register_passwords()."""
```

- `UserSpec` gains `extra_fields: dict[str, object] = field(default_factory=dict)`.
- `with_user` gains keyword param `extra_fields: dict[str, object] | None = None`, passes `extra_fields=extra_fields or {}` into `UserSpec(...)`, and documents it: "extra_fields: Additional registration-schema fields for custom user models."
- In `build()`, replace the user-creation block:

```python
        # Create users using the kernel's registered registration schema
        registration_schema = get_kernel().schemas.registration
        for user_spec in self._user_specs:
            user = get_kernel().crud_users.create(
                obj_in=registration_schema(
                    name=user_spec.name,
                    surname=user_spec.surname,
                    email=user_spec.email,
                    password=user_spec.password,
                    is_active=user_spec.is_active,
                    **user_spec.extra_fields,
                ),
                context=no_user_context,
            )
            result.users[user_spec.name] = user
            result.passwords[user.email] = user_spec.password
```

(the role-assignment loop below it is unchanged).

- [ ] **Step 4: Modify `src/kwik/testing/fixtures/factories.py`**

`user_factory`'s inner `_create_user` gains `extra_fields: dict[str, object] | None = None` (keyword-only, after `roles`) and forwards `extra_fields=extra_fields` to `scenario.with_user(...)`. Update its docstring accordingly. In `TYPE_CHECKING`, replace `User` with `UserMixin` (import from `kwik.models`) in imports and return-type annotations.

- [ ] **Step 5: Modify `src/kwik/testing/client.py`**

- In `TYPE_CHECKING`, replace `from kwik.models import User` with `from kwik.models.user_mixin import UserMixin`, and replace all `user: User` parameter annotations with `user: UserMixin`.
- In `__init__`, add `self._passwords: dict[str, str] = {}`.
- Add after `__init__`:

```python
    def register_passwords(self, passwords: dict[str, str]) -> None:
        """
        Register email -> plaintext password pairs for authentication.

        Pass ``ScenarioResult.passwords`` so the client can authenticate scenario
        users created with non-default passwords.
        """
        self._passwords.update(passwords)
```

- In `_get_auth_token`, replace the password-selection block:

```python
        # Registered passwords first (ScenarioResult.passwords), then legacy fallbacks
        password = self._passwords.get(user.email)
        if password is None:
            if user.email == "regular@example.com":
                password = "regularpassword123"  # noqa: S105
            elif self._settings and user.email == self._settings.FIRST_SUPERUSER:
                password = self._settings.FIRST_SUPERUSER_PASSWORD
            else:
                password = "testpassword123"  # Default test password  # noqa: S105
```

- [ ] **Step 6: Write the new tests**

`tests/test_seeding.py`:

```python
"""Tests for the first-superuser seeding battery."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.seeding import ADMIN_ROLE_NAME, create_first_superuser

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.settings import BaseKwikSettings


class TestCreateFirstSuperuser:
    def test_is_idempotent(self, session: Session, settings: BaseKwikSettings) -> None:
        first = create_first_superuser(session=session, settings=settings)
        second = create_first_superuser(session=session, settings=settings)
        assert first.id == second.id

    def test_superuser_has_admin_role_with_all_permissions(
        self, session: Session, settings: BaseKwikSettings
    ) -> None:
        user = create_first_superuser(session=session, settings=settings)
        assert ADMIN_ROLE_NAME in {role.name for role in user.roles}
        assert {permission.name for permission in user.permissions} == {p.value for p in Permissions}
```

`tests/testing/test_scenario_passwords.py`:

```python
"""Tests for ScenarioResult password recording."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.testing import Scenario

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models.user_mixin import UserMixin


class TestScenarioPasswords:
    def test_build_records_passwords_by_email(self, session: Session, admin_user: UserMixin) -> None:
        result = (
            Scenario()
            .with_user(name="pwuser", password="secretpw123")
            .build(session=session, admin_user=admin_user)
        )
        assert result.passwords["pwuser@test.com"] == "secretpw123"
```

`tests/api/test_client_passwords.py`:

```python
"""Tests for IdentityAwareTestClient password registration."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.models.user_mixin import UserMixin
    from kwik.testing import IdentityAwareTestClient


class TestRegisteredPasswords:
    def test_registered_password_is_used_for_login(
        self,
        identity_aware_client: IdentityAwareTestClient,
        user_factory: Callable[..., UserMixin],
    ) -> None:
        user = user_factory(name="custompw", password="anotherpw456")
        identity_aware_client.register_passwords({user.email: "anotherpw456"})
        response = identity_aware_client.get_as(user, "/api/v1/users/me")
        assert response.status_code == HTTPStatus.OK
```

(Without `register_passwords`, the legacy fallback would try `testpassword123` and authentication would fail — this test proves the registry path.)

- [ ] **Step 7: Run new tests, then full suite**

Run: `uv run pytest tests/test_seeding.py tests/testing/test_scenario_passwords.py tests/api/test_client_passwords.py -n 0 -v` → PASS.
Run: `uv run pytest` → all pass (admin fixture now seeds through the battery — same data as before).

- [ ] **Step 8: Lint, format, commit**

```bash
uv run ruff check && uv run ruff format
git add src/kwik/seeding.py src/kwik/testing/ tests/test_seeding.py tests/testing/test_scenario_passwords.py tests/api/test_client_passwords.py
git commit -S -m "feat: seeding battery, scenario extra_fields/passwords, client password registry"
```

---

### Task 9: Kernel DI methods, router factories, and the 2.0 public surface

**Files:**
- Modify: `src/kwik/kernel.py` (DI methods + router factory methods)
- Modify: `src/kwik/api/endpoints/users.py`, `src/kwik/api/endpoints/login.py`, `src/kwik/api/endpoints/roles.py` (factory conversion — full rewrites below)
- Modify: `src/kwik/api/endpoints/__init__.py`
- Delete: `src/kwik/api/api.py`
- Modify: `src/kwik/crud/users.py`, `src/kwik/crud/__init__.py` (delete transitional singleton)
- Modify: `src/kwik/__init__.py`, `src/kwik/__main__.py`
- Modify: `tests/api/conftest.py`, `tests/applications/test_kwik.py`
- Modify: `tests/security/test_security.py`, `tests/testing/conftest.py`, `tests/testing/test_scenario.py`, `tests/crud/test_crud_roles.py`, `tests/crud/test_crud_users.py` (crud_users sweep)
- Create: `tests/api/test_router_composition.py`
- Modify: `pyproject.toml` (ruff per-file-ignores)

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `Kernel.get_current_user(user) -> UserT`, `Kernel.get_resolved_user(user) -> UserT`, `Kernel.get_user_context(session, user) -> Context[UserT]` — FastAPI dependency callables (bound methods; use as `Annotated[AppUser, Depends(kernel.get_current_user)]`).
  - `Kernel.create_users_router() -> AuthenticatedRouter`, `Kernel.create_login_router() -> APIRouter`, `Kernel.create_roles_router() -> AuthenticatedRouter`, `Kernel.create_api_router(*, login=True, users=True, roles=True, permissions=True) -> APIRouter`.
  - Module factories `create_users_router(kernel)`, `create_login_router(kernel)`, `create_roles_router(kernel)` in `kwik.api.endpoints`.
  - `kwik` top level: `Kernel`, `UserSchemas`, `UserMixin`, `Kwik`, `run`, `testing`, `NoUserContext`, `UserContext`, `current_user`, `resolved_user`. REMOVED: `kwik.api_router`, `kwik.api.api`, `kwik.crud.crud_users`, module-level `users_router`/`login_router`/`roles_router`.

- [ ] **Step 1: Add DI + factory methods to `src/kwik/kernel.py`**

Add to the module imports (all safe: none of these modules imports `kwik.kernel` at module scope):

```python
from typing import Annotated, Final, cast

from fastapi import APIRouter, Depends

from kwik.crud.context import Context
from kwik.dependencies.session import Session
from kwik.dependencies.users import _get_current_user, _resolve_current_user
from kwik.routers import AuthenticatedRouter
```

Add these methods to `Kernel` (after `__init__`):

```python
    def get_current_user(self, user: Annotated[UserMixin, Depends(_get_current_user)]) -> UserT:
        """FastAPI dependency: the JWT-authenticated user, typed as the registered model."""
        return cast("UserT", user)

    def get_resolved_user(self, user: Annotated[UserMixin, Depends(_resolve_current_user)]) -> UserT:
        """FastAPI dependency: the JWT-or-API-key authenticated user, typed as the registered model."""
        return cast("UserT", user)

    def get_user_context(
        self,
        session: Session,
        user: Annotated[UserMixin, Depends(_get_current_user)],
    ) -> Context[UserT]:
        """FastAPI dependency: an authenticated CRUD context typed against the registered model."""
        return Context(session=session, user=cast("UserT", user))

    def create_users_router(self) -> AuthenticatedRouter:
        """Build the /users router bound to this kernel's model and schemas."""
        from kwik.api.endpoints.users import create_users_router  # noqa: PLC0415 — deferred: endpoints import kwik deps

        return create_users_router(self)

    def create_login_router(self) -> APIRouter:
        """Build the /login router bound to this kernel's model and schemas."""
        from kwik.api.endpoints.login import create_login_router  # noqa: PLC0415 — deferred: endpoints import kwik deps

        return create_login_router(self)

    def create_roles_router(self) -> AuthenticatedRouter:
        """Build the /roles router bound to this kernel's model and schemas."""
        from kwik.api.endpoints.roles import create_roles_router  # noqa: PLC0415 — deferred: endpoints import kwik deps

        return create_roles_router(self)

    def create_api_router(
        self,
        *,
        login: bool = True,
        users: bool = True,
        roles: bool = True,
        permissions: bool = True,
    ) -> APIRouter:
        """Assemble kwik's built-in routers; each is individually opt-out-able."""
        router = APIRouter()
        if login:
            router.include_router(self.create_login_router())
        if users:
            router.include_router(self.create_users_router())
        if roles:
            router.include_router(self.create_roles_router())
        if permissions:
            from kwik.api.endpoints.permissions import permissions_router  # noqa: PLC0415

            router.include_router(permissions_router)
        return router
```

(`_get_current_user`/`_resolve_current_user` are private helpers of `kwik.dependencies.users` — importing them here is deliberate framework-internal reuse; add `# noqa: PLC2701` on that import line if ruff flags private-name import.)

- [ ] **Step 2: Rewrite `src/kwik/api/endpoints/users.py`**

```python
"""User management API endpoints (kernel-bound factory)."""

# NOTE: no `from __future__ import annotations` — request/response schemas are
# resolved from the kernel at factory-call time and must evaluate eagerly.

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.dependencies import ListQuery, UserContext, current_user, has_permission
from kwik.exceptions import DuplicatedEntityError
from kwik.models.user_mixin import UserMixin
from kwik.routers import AuthenticatedRouter
from kwik.schemas import AdminPasswordReset, Paginated, PermissionProfile, RoleProfile, UserPasswordChange

if TYPE_CHECKING:
    from kwik.kernel import Kernel
    from kwik.models import Permission, Role


def create_users_router(kernel: "Kernel[UserMixin]") -> AuthenticatedRouter:  # noqa: PLR0915
    """Build the /users router bound to the kernel's registered model and schemas."""
    crud_users = kernel.crud_users
    profile_schema = kernel.schemas.profile
    registration_schema = kernel.schemas.registration
    update_schema = kernel.schemas.update

    router = AuthenticatedRouter(prefix="/users")

    @router.get("/", response_model=Paginated[profile_schema], dependencies=(has_permission(Permissions.user_read),))
    def read_users(q: ListQuery, context: UserContext) -> dict[str, object]:
        """Retrieve users."""
        total, data = crud_users.get_multi(context=context, **q)
        return {"total": total, "data": data}

    @router.post("/", response_model=profile_schema, dependencies=(has_permission(Permissions.user_create),))
    def create_user(user_in: registration_schema, context: UserContext) -> UserMixin:
        """Create new user."""
        user = crud_users.get_by_email(email=user_in.email, context=context)
        if user:
            raise DuplicatedEntityError

        return crud_users.create(obj_in=user_in, context=context)

    @router.get("/me", response_model=profile_schema)
    def read_user_me(user: current_user) -> UserMixin:
        """Get current user."""
        return user

    @router.put("/me", response_model=profile_schema)
    def update_myself(user: current_user, user_in: update_schema, context: UserContext) -> UserMixin:
        """Update details of the logged in user."""
        return crud_users.update(entity_id=user.id, obj_in=user_in, context=context)

    @router.get("/me/permissions", response_model=list[PermissionProfile])
    def read_permissions_of_current_user(user: current_user) -> "list[Permission]":
        """Get all effective permissions of the current logged-in user."""
        return crud_users.get_permissions(user=user)

    @router.get("/me/roles", response_model=list[RoleProfile])
    def read_roles_of_current_user(user: current_user) -> "list[Role]":
        """Get roles of the current logged-in user."""
        return crud_users.get_roles(user=user)

    @router.put("/me/password", response_model=profile_schema)
    def update_my_password(user: current_user, obj_in: UserPasswordChange, context: UserContext) -> UserMixin:
        """Update current user's password."""
        return crud_users.change_password(user_id=user.id, obj_in=obj_in, context=context)

    @router.get("/{user_id}", response_model=profile_schema, dependencies=(has_permission(Permissions.user_read),))
    def read_user_by_id(user_id: int, context: UserContext) -> UserMixin:
        """Get a specific user by id."""
        return crud_users.get_if_exist(entity_id=user_id, context=context)

    @router.put("/{user_id}", response_model=profile_schema, dependencies=(has_permission(Permissions.user_update),))
    def update_user(user_id: int, user_in: update_schema, context: UserContext) -> UserMixin:
        """Update a user."""
        return crud_users.update(entity_id=user_id, obj_in=user_in, context=context)

    @router.get(
        "/{user_id}/permissions",
        response_model=list[PermissionProfile],
        dependencies=(
            has_permission(Permissions.user_read),
            has_permission(Permissions.permission_read),
        ),
    )
    def read_user_permissions(user_id: int, context: UserContext) -> "list[Permission]":
        """Get all effective permissions for a specific user."""
        user = crud_users.get_if_exist(entity_id=user_id, context=context)
        return crud_users.get_permissions(user=user)

    @router.get(
        "/{user_id}/roles",
        response_model=list[RoleProfile],
        dependencies=(
            has_permission(
                Permissions.user_read,
                Permissions.role_read,
            ),
        ),
    )
    def read_user_roles(user_id: int, context: UserContext) -> "list[Role]":
        """Get all roles assigned to a specific user."""
        user = crud_users.get_if_exist(entity_id=user_id, context=context)
        return crud_users.get_roles(user=user)

    @router.put(
        "/{user_id}/password",
        response_model=profile_schema,
        dependencies=(has_permission(Permissions.user_update),),
    )
    def update_password(user_id: int, obj_in: UserPasswordChange, context: UserContext) -> UserMixin:
        """Update user's password (admin operation)."""
        return crud_users.change_password(user_id=user_id, obj_in=obj_in, context=context)

    @router.put(
        "/{user_id}/reset-password",
        response_model=profile_schema,
        dependencies=(has_permission(Permissions.password_reset),),
    )
    def admin_reset_password(user_id: int, obj_in: AdminPasswordReset, context: UserContext) -> UserMixin:
        """Reset user's password (admin operation, no old password required)."""
        return crud_users.admin_reset_password(user_id=user_id, password=obj_in.new_password, context=context)

    return router


__all__ = ["create_users_router"]
```

(`AdminPasswordReset` and `UserPasswordChange` are fixed kwik schemas, not kernel-bound — they stay as ordinary top-level imports.)

- [ ] **Step 3: Rewrite `src/kwik/api/endpoints/login.py`**

```python
"""Authentication and login API endpoints (kernel-bound factory)."""

# NOTE: no `from __future__ import annotations` — the profile response schema is
# resolved from the kernel at factory-call time and must evaluate eagerly.

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.security import OAuth2PasswordRequestForm

from kwik.core.enum import Permissions
from kwik.dependencies import NoUserContext, Settings, UserContext, current_token, current_user, has_permission
from kwik.exceptions.base import TokenValidationError
from kwik.models.user_mixin import UserMixin
from kwik.schemas import Token
from kwik.security import create_token, verify_password_reset_token

if TYPE_CHECKING:
    from kwik.kernel import Kernel


def create_login_router(kernel: "Kernel[UserMixin]") -> APIRouter:
    """Build the /login router bound to the kernel's registered model and schemas."""
    crud_users = kernel.crud_users
    profile_schema = kernel.schemas.profile

    router = APIRouter(prefix="/login", tags=["login"])

    @router.post("/access-token", response_model=Token)
    def login_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        settings: Settings,
        context: NoUserContext,
    ) -> Token:
        """
        OAuth2 compatible token login, get an access token for future requests.

        Raises:
            IncorrectCredentials: If the provided credentials are incorrect

        """
        user = crud_users.authenticate(email=form_data.username, password=form_data.password, context=context)
        return create_token(user_id=user.id, settings=settings)

    @router.post("/test-token", response_model=profile_schema)
    def test_token(user: current_user) -> UserMixin:
        """Test access token."""
        return user

    @router.post(
        "/impersonate",
        response_model=Token,
        dependencies=(has_permission(Permissions.impersonification),),
    )
    def impersonate(
        user_id: int,
        user: current_user,
        settings: Settings,
        context: UserContext,
    ) -> Token:
        """Impersonate a user."""
        user_to_impersonate = crud_users.get_if_exist(entity_id=user_id, context=context)
        return create_token(user_id=user_to_impersonate.id, impersonator_user_id=user.id, settings=settings)

    @router.post("/is_impersonating", response_model=bool)
    def is_impersonating(token: current_token) -> bool:
        return token.kwik_impersonate != ""

    @router.post("/stop_impersonating", response_model=Token)
    def stop_impersonating(token: current_token, settings: Settings) -> Token:
        """
        Stop impersonating and return the original token.

        Raises:
            InvalidToken: If the token is invalid

        """
        return create_token(user_id=int(token.kwik_impersonate), settings=settings)

    @router.post("/reset-password")
    def reset_password(
        token: Annotated[str, Body()],
        password: Annotated[str, Body()],
        settings: Settings,
        context: NoUserContext,
    ) -> dict:
        """Reset password using a self-service reset token (no authentication required)."""
        email = verify_password_reset_token(token=token, settings=settings, context=context)
        if not email:
            raise TokenValidationError

        crud_users.reset_password(email=email, password=password, context=context)
        return {"msg": "Password updated successfully"}

    return router


__all__ = ["create_login_router"]
```

- [ ] **Step 4: Rewrite `src/kwik/api/endpoints/roles.py`**

Same conversion: `def create_roles_router(kernel: "Kernel[UserMixin]") -> AuthenticatedRouter:  # noqa: PLR0915` wrapping ALL current endpoints verbatim with these mechanical substitutions — the file loses `from __future__ import annotations` and the `UserProfile` import, gains `from kwik.models.user_mixin import UserMixin` and the `TYPE_CHECKING` `Kernel` import, and binds `crud_users = kernel.crud_users` / `profile_schema = kernel.schemas.profile` at the top of the factory:
- `roles_router = AuthenticatedRouter(prefix="/roles")` → `router = AuthenticatedRouter(prefix="/roles")` inside the factory; every `@roles_router.` → `@router.`; `return router` at the end; `__all__ = ["create_roles_router"]`.
- `users_with_role` and `available_users_for_role`: `response_model=list[UserProfile]` → `response_model=list[profile_schema]`; return annotations `-> list[User]` → `-> "list[UserMixin]"`.
- All other endpoints (read_roles, create_role, read_role_by_id, update_role, delete_role, read_permissions_by_role, read_available_permissions_for_role, assign_permission_to_role, remove_permission_from_role, assign_user_to_role, remove_user_from_role, remove_all_permissions_from_role, remove_all_users_from_role) keep their exact decorators, signatures, docstrings, and bodies — `crud_roles`/`crud_permissions` imports unchanged; only the two `crud_users.get_if_exist` call sites now hit the factory-bound `crud_users`.
- Return annotations referencing `Role`/`Permission` stay as string literals (`-> "Role"`, `-> "list[Permission]"`) with the classes under `TYPE_CHECKING` — FastAPI ignores return annotations when `response_model` is set, so unresolvable strings are fine there, and eager evaluation is only mandatory for PARAMETER annotations (`role_in: RoleDefinition` etc. — keep those schemas as runtime imports: `from kwik.schemas import Paginated, PermissionProfile, RoleDefinition, RolePermissionAssignment, RoleProfile, RoleUpdate, RoleUserAssignment`).

- [ ] **Step 5: Update `src/kwik/api/endpoints/__init__.py`, delete `src/kwik/api/api.py`**

```python
"""
API endpoints package for kwik framework.

This package contains FastAPI endpoint factories and routers for the kwik web framework.
"""

from __future__ import annotations

from .login import create_login_router
from .permissions import permissions_router
from .roles import create_roles_router
from .users import create_users_router

__all__ = ["create_login_router", "create_roles_router", "create_users_router", "permissions_router"]
```

Run: `git rm src/kwik/api/api.py`

- [ ] **Step 6: Delete the transitional users-CRUD singleton**

In `src/kwik/crud/users.py`: delete the `crud_users = CRUDUsers(model=User)` line, its TRANSITIONAL comment, and the `from kwik.models import User` import; `__all__ = ["CRUDUsers"]`.
In `src/kwik/crud/__init__.py`: `from .users import CRUDUsers` and remove `"crud_users"` from `__all__`.

- [ ] **Step 7: Rewrite `src/kwik/__init__.py` and update `src/kwik/__main__.py`**

`src/kwik/__init__.py`:

```python
"""
Kwik - A modern, batteries-included web framework for building RESTful backends with Python.

Kwik is built on FastAPI and provides an opinionated, business-oriented API for rapid development.

Consuming applications register their user model once via ``kwik.Kernel`` and build
the API router from it::

    kernel = kwik.Kernel(user_model=AppUser, schemas=kwik.UserSchemas(...))
    app = kwik.Kwik(settings=Settings(), api_router=kernel.create_api_router())

The testing module provides enhanced testing utilities for Kwik applications:
    from kwik.testing import Scenario, IdentityAwareTestClient
"""

from __future__ import annotations

from . import testing
from .applications import Kwik, run
from .dependencies import NoUserContext, UserContext, current_user, resolved_user
from .kernel import Kernel, UserSchemas
from .models.user_mixin import UserMixin

__all__ = [
    "Kernel",
    "Kwik",
    "NoUserContext",
    "UserContext",
    "UserMixin",
    "UserSchemas",
    "current_user",
    "resolved_user",
    "run",
    "testing",
]
```

`src/kwik/__main__.py`: replace `from kwik.api.api import api_router` with `from kwik.kernel import get_kernel`, and in the default mode:

```python
        kwik_app = Kwik(settings=settings, api_router=get_kernel().create_api_router())
```

(update the module docstring line "Uses the standard API router from kwik.api.api" → "Builds the standard API router from the default kernel").

- [ ] **Step 8: Update test fixtures/imports that referenced the removed surface**

`tests/api/conftest.py`: replace `from kwik.api.api import api_router` with `from kwik.kernel import get_kernel`, and:

```python
@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Create and return a Kwik application instance for testing."""
    return Kwik(settings=settings, api_router=get_kernel().create_api_router())
```

`tests/applications/test_kwik.py`: replace `from kwik.api.api import api_router` with:

```python
from kwik.kernel import get_kernel

api_router = get_kernel().create_api_router()
```

(all 10 `Kwik(settings=..., api_router=api_router, ...)` usages then work unchanged).

crud_users sweep — in each of `tests/security/test_security.py`, `tests/testing/conftest.py`, `tests/testing/test_scenario.py`, `tests/crud/test_crud_roles.py`, `tests/crud/test_crud_users.py`: replace the `crud_users` import (however it appears, e.g. `from kwik.crud import crud_users`) with:

```python
from kwik.kernel import get_kernel

crud_users = get_kernel().crud_users
```

at module level (main-suite test modules are imported after plugins/conftest, so a module-level `get_kernel()` call is safe HERE — never in kwik source). If the file imports other names from `kwik.crud` in the same line, keep those.

- [ ] **Step 9: New composition test — `tests/api/test_router_composition.py`**

```python
"""Tests for Kernel.create_api_router composition flags."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.kernel import get_kernel

if TYPE_CHECKING:
    from fastapi import APIRouter


def _route_paths(router: APIRouter) -> set[str]:
    return {route.path for route in router.routes}


class TestCreateApiRouter:
    def test_default_includes_all_builtin_routers(self) -> None:
        paths = _route_paths(get_kernel().create_api_router())
        assert any(path.startswith("/users") for path in paths)
        assert any(path.startswith("/login") for path in paths)
        assert any(path.startswith("/roles") for path in paths)
        assert any(path.startswith("/permissions") for path in paths)

    def test_users_router_can_be_excluded(self) -> None:
        paths = _route_paths(get_kernel().create_api_router(users=False))
        assert not any(path.startswith("/users") for path in paths)
        assert any(path.startswith("/login") for path in paths)

    def test_only_login_router(self) -> None:
        paths = _route_paths(get_kernel().create_api_router(users=False, roles=False, permissions=False))
        assert paths
        assert all(path.startswith("/login") for path in paths)
```

- [ ] **Step 10: ruff per-file-ignores for the factory modules**

In `pyproject.toml` under `[tool.ruff.lint.per-file-ignores]` add:

```toml
"src/kwik/api/endpoints/users.py" = ["FA100", "FA102"]
"src/kwik/api/endpoints/login.py" = ["FA100", "FA102"]
"src/kwik/api/endpoints/roles.py" = ["FA100", "FA102"]
```

- [ ] **Step 11: Verify the old surface is gone**

Run: `grep -rn "api_router" src/kwik/ | grep -v create_api_router`
Expected: no hits (no module-level `api_router` singleton anywhere).
Run: `grep -rn "crud_users" src/kwik/ | grep -v "kernel\|crud_users = kernel\|self\."`
Expected: hits only where resolved via `get_kernel().crud_users` or `kernel.crud_users`.
Run: `grep -rn "users_router\|login_router\|roles_router" src/ tests/`
Expected: only `permissions_router` remains as a module-level router; factories otherwise.

- [ ] **Step 12: Full suite, lint, commit**

Run: `uv run pytest` → all pass (API tests now exercise the factory-built routers end to end).

```bash
uv run ruff check && uv run ruff format
git add -A
git commit -S -m "feat!: kernel-bound router factories and 2.0 public surface"
```

---

### Task 10: Remove the transitional `User` alias; enforce lazy `DefaultUser`

**Files:**
- Modify: `src/kwik/models/__init__.py`
- Modify (import sweep): `tests/security/test_security.py`, `tests/utils/helpers.py`, `tests/testing/test_client.py`, `tests/testing/test_factories.py`, `tests/testing/conftest.py`, `tests/testing/test_client_auth.py`, `tests/crud/test_crud_users.py`, `tests/crud/test_crud_roles.py`, `tests/api/test_permissions_router.py`, `tests/api/test_login_router.py`, `tests/api/test_users_router.py`, `tests/api/test_roles_router.py`, `tests/dependencies/test_api_key.py`, `tests/test_kernel.py`
- Create: `tests/test_lazy_default_user.py`
- Modify: `.github/workflows/test.yml` (package-test lazy assertion)

**Interfaces:**
- Consumes: everything above.
- Produces: `kwik.models` exports NO `User` name; `DefaultUser` importable only from `kwik.models.default_user` and mapped only on first `get_kernel()`. Test annotations use `UserMixin`.

- [ ] **Step 1: Remove the alias from `src/kwik/models/__init__.py`**

Delete the `from .default_user import DefaultUser as User` import (and its TRANSITIONAL comment) and remove `"User"` from `__all__`.

- [ ] **Step 2: Sweep the TYPE_CHECKING-only test imports**

In each of `tests/security/test_security.py:28`, `tests/utils/helpers.py:11`, `tests/testing/test_client.py:16`, `tests/testing/test_factories.py:12`, `tests/testing/conftest.py:19`, `tests/testing/test_client_auth.py:13`, `tests/crud/test_crud_users.py:17`, `tests/crud/test_crud_roles.py:17`, `tests/api/test_permissions_router.py:19`, `tests/api/test_login_router.py:24`, `tests/api/test_users_router.py:20`, `tests/api/test_roles_router.py:20` (line numbers as of Task 9 may have shifted — locate with the grep below):

1. In the `from kwik.models import ...` line, replace the name `User` with `UserMixin` (keep other imported names like `Permission`, `Role`).
2. Then in that file, replace every remaining type-annotation reference `User` with `UserMixin` — find them first with `grep -n "\bUser\b" <file>` and update each (they are annotations only in these files; do not touch `UserRole`, `UserMixin`, `UserProfile`, etc.).

- [ ] **Step 3: Sweep the runtime imports**

`tests/dependencies/test_api_key.py:23` — replace:

```python
from kwik.models.user import Permission, Role, RolePermission, User, UserRole
```

with:

```python
from kwik.models.default_user import DefaultUser as User
from kwik.models.user import Permission, Role, RolePermission, UserRole
```

(the local `User` name keeps the rest of the file unchanged; the eager `DefaultUser` import is correct in the main suite, where it IS the active model).

`tests/test_kernel.py` — replace the import `from kwik.models import Base, Role, User, UserMixin` with `from kwik.models import Base, Role, UserMixin` plus `from kwik.models.default_user import DefaultUser`, then replace exactly these usages: every `user_model=User` → `user_model=DefaultUser`, `kernel.user_model is User` → `kernel.user_model is DefaultUser`, `kernel.crud_users.model is User` → `kernel.crud_users.model is DefaultUser`. (Leave `UserSchemas`, `UserMixin`, `UserProfile*` names untouched.)

- [ ] **Step 4: Write the lazy-mapping guard test — `tests/test_lazy_default_user.py`**

```python
"""Guard: importing kwik must not map DefaultUser (custom apps map their own users table)."""

from __future__ import annotations

import subprocess
import sys

_PROBE = (
    "import kwik; from kwik.models import Base; "
    "assert 'users' not in Base.metadata.tables, 'DefaultUser must not be eagerly mapped'"
)


def test_default_user_not_mapped_on_bare_import() -> None:
    """Run the probe in a fresh interpreter: the main test process has DefaultUser mapped already."""
    subprocess.run([sys.executable, "-c", _PROBE], check=True)  # noqa: S603
```

- [ ] **Step 5: Add the same guard to the package-test CI job**

In `.github/workflows/test.yml`, `package-test` job, append to the "Test package imports" step's script:

```yaml
        python -c "import kwik; from kwik.models import Base; assert 'users' not in Base.metadata.tables, 'DefaultUser must not be eagerly mapped'"
```

- [ ] **Step 6: Verify, run, commit**

Run: `grep -rn "from kwik.models import.*\bUser\b\|from kwik.models.user import.*\bUser\b" src/ tests/ | grep -v "UserMixin\|UserRole\|UserTrackingMixin"`
Expected: no hits.
Run: `grep -rn "default_user" src/kwik/`
Expected: only `src/kwik/models/default_user.py` itself and the lazy import inside `get_kernel()`.
Run: `uv run pytest && uv run ruff check && uv run ruff format`

```bash
git add -A
git commit -S -m "feat!: drop User export; DefaultUser is lazily mapped only"
```

---

### Task 11: Custom-user test session + typing contract + CI

**Files:**
- Create: `tests_custom_user/conftest.py`
- Create: `tests_custom_user/test_custom_user_crud.py`
- Create: `tests_custom_user/test_custom_user_api.py`
- Create: `tests_custom_user/test_typing_contract.py`
- Modify: `pyproject.toml` (pyright dev dep + config + ruff ignores for the new dir)
- Modify: `.github/workflows/test.yml`

**Interfaces:**
- Consumes: the full kernel mechanism.
- Produces: a SEPARATE pytest session (`uv run pytest tests_custom_user -p kwik.testing.fixtures -n 0`) proving the mechanism end-to-end with a custom model, plus a pyright-checked typing contract. `tests_custom_user/` sits at the repo root, OUTSIDE `testpaths = ["tests"]`, because one kernel per process is a hard constraint — it must never be collected with the main suite.

- [ ] **Step 1: Create `tests_custom_user/conftest.py`**

```python
"""
Custom-user test session: registers a custom user model BEFORE any fixture runs.

This suite runs as a SEPARATE pytest session (see .github/workflows/test.yml):
one kernel per process is a hard constraint, so these tests must never be
collected together with the main suite (which uses DefaultUser). The kwik
fixtures plugin is loaded via `-p kwik.testing.fixtures` on the command line.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from kwik.applications import Kwik
from kwik.database import create_session
from kwik.dependencies.session import _get_session
from kwik.kernel import Kernel, UserSchemas
from kwik.models import Base, UserMixin
from kwik.schemas import UserProfile, UserProfileUpdate, UserRegistration
from kwik.testing import IdentityAwareTestClient

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from kwik.settings import BaseKwikSettings


class CustomTestUser(Base, UserMixin):
    """Custom user model with one extra column, mirroring a consuming application."""

    __tablename__ = "users"

    nickname: Mapped[str] = mapped_column(String, default="", nullable=False)


class CustomUserProfile(UserProfile):
    """Profile schema exposing the custom column."""

    nickname: str


class CustomUserRegistration(UserRegistration):
    """Registration schema accepting the custom column."""

    nickname: str = ""


class CustomUserUpdate(UserProfileUpdate):
    """Update schema accepting the custom column."""

    nickname: str | None = None


KERNEL = Kernel(
    user_model=CustomTestUser,
    schemas=UserSchemas(profile=CustomUserProfile, registration=CustomUserRegistration, update=CustomUserUpdate),
)


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Kwik application built from the custom kernel."""
    return Kwik(settings=settings, api_router=KERNEL.create_api_router())


@pytest.fixture
def client(kwik_app: Kwik, engine: Engine) -> Generator[TestClient, None, None]:
    """HTTP client with a rolled-back session per test (mirrors tests/api/conftest.py)."""
    api_session = create_session(engine=engine)

    def _get_session_override() -> Generator[Session, None, None]:
        yield api_session

    kwik_app.app.dependency_overrides[_get_session] = _get_session_override

    with TestClient(app=kwik_app.app) as client:
        yield client

    api_session.rollback()
    api_session.close()


@pytest.fixture
def identity_aware_client(client: TestClient, settings: BaseKwikSettings) -> IdentityAwareTestClient:
    """TestClient with identity-aware authentication context switching."""
    return IdentityAwareTestClient(client, settings)
```

(Move the `TYPE_CHECKING` import block up with the other imports when writing the file — shown inline here for clarity. Ruff will enforce ordering.)

- [ ] **Step 2: Create `tests_custom_user/test_custom_user_crud.py`**

```python
"""CRUD, scenario, and seeding behavior against a custom user model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.kernel import get_kernel
from kwik.seeding import create_first_superuser

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from kwik.crud import NoUserCtx
    from kwik.models import UserMixin
    from kwik.settings import BaseKwikSettings


class TestCustomUserCrud:
    def test_create_persists_custom_column_on_single_table(self, no_user_context: NoUserCtx) -> None:
        kernel = get_kernel()
        registration = kernel.schemas.registration(
            name="ace",
            surname="Custom",
            email="ace@test.com",
            password="acepassword123",
            nickname="Ace",
        )
        user = kernel.crud_users.create(obj_in=registration, context=no_user_context)
        assert type(user) is kernel.user_model
        assert user.nickname == "Ace"

    def test_user_factory_forwards_extra_fields(self, user_factory: Callable[..., UserMixin]) -> None:
        user = user_factory(name="zed", extra_fields={"nickname": "Zed"})
        assert user.nickname == "Zed"

    def test_seeding_accepts_extra_fields(self, session: Session, settings: BaseKwikSettings) -> None:
        alt_settings = settings.model_copy(update={"FIRST_SUPERUSER": "root2@example.com"})
        superuser = create_first_superuser(session=session, settings=alt_settings, nickname="Root")
        assert superuser.nickname == "Root"
```

- [ ] **Step 3: Create `tests_custom_user/test_custom_user_api.py`**

```python
"""API behavior: registered schemas bind to request bodies and response models."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kwik.models import UserMixin
    from kwik.testing import IdentityAwareTestClient


class TestCustomUserApi:
    def test_me_exposes_custom_field(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: UserMixin
    ) -> None:
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/me")
        assert response.status_code == HTTPStatus.OK
        assert "nickname" in response.json()

    def test_create_user_accepts_custom_field(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: UserMixin
    ) -> None:
        payload = {
            "name": "nova",
            "surname": "Custom",
            "email": "nova@test.com",
            "password": "novapassword123",
            "nickname": "Nova",
        }
        response = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=payload)
        assert response.status_code == HTTPStatus.OK
        assert response.json()["nickname"] == "Nova"
```

- [ ] **Step 4: Create `tests_custom_user/test_typing_contract.py`**

```python
"""
Static typing contract for the kernel — checked by pyright in CI.

The probe functions are never executed; pyright verifies the assert_type claims.
ContractUser is deliberately NOT mapped (no Base subclass): pytest imports this
module in the custom-user session, and a second mapped "users" class would clash.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_type

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.crud.context import Context, MaybeUserCtx
    from kwik.crud.users import CRUDUsers
    from kwik.kernel import Kernel

from kwik.models import UserMixin


class ContractUser(UserMixin):
    """Typing-only stand-in for a custom user model."""

    nickname: str


def _probe_kernel_typing(kernel: Kernel[ContractUser], context: MaybeUserCtx, some_user: UserMixin) -> None:
    assert_type(kernel.user_model, type[ContractUser])
    assert_type(kernel.crud_users, CRUDUsers[ContractUser])
    maybe_user = kernel.crud_users.get(entity_id=1, context=context)
    assert_type(maybe_user, ContractUser | None)
    assert_type(kernel.get_current_user(user=some_user), ContractUser)
    assert_type(kernel.get_resolved_user(user=some_user), ContractUser)


def _probe_context_typing(kernel: Kernel[ContractUser], db_session: Session, some_user: UserMixin) -> None:
    ctx = kernel.get_user_context(session=db_session, user=some_user)
    assert_type(ctx, Context[ContractUser])
    assert_type(ctx.user, ContractUser)


def test_contract_module_imports() -> None:
    """The probes above are static-only; this keeps pytest collection meaningful."""
    assert callable(_probe_kernel_typing)
    assert callable(_probe_context_typing)
```

NOTE: if pyright cannot evaluate `assert_type` targets through the `TYPE_CHECKING`-guarded imports, move those imports out of the guard (they are all runtime-safe). Adjust until `uv run pyright tests_custom_user/test_typing_contract.py` reports 0 errors — the contract is the pyright result, not the import style.

- [ ] **Step 5: pyproject — pyright dep/config + ruff ignores**

- Add to `[dependency-groups] dev`: `"pyright>=1.1.390",`
- Add sections:

```toml
[tool.pyright]
venvPath = "."
venv = ".venv"
```

- Add to `[tool.ruff.lint.per-file-ignores]`:

```toml
"tests_custom_user/*.py" = ["S101", "S105", "S106", "S107", "S311", "SLF001", "N805"]
```

- Run `uv sync` after editing dependencies.

- [ ] **Step 6: Run the custom session and pyright locally**

Run: `uv run pytest tests_custom_user -p kwik.testing.fixtures -n 0`
Expected: all custom-user tests pass (fresh process, custom kernel claims the slot before fixtures run).
Run: `uv run pytest`
Expected: main suite still green and does NOT collect `tests_custom_user` (testpaths).
Run: `uv run pyright tests_custom_user/test_typing_contract.py`
Expected: `0 errors, 0 warnings`.

- [ ] **Step 7: Wire CI**

In `.github/workflows/test.yml`, `test` job, after the "Run tests" step:

```yaml
    - name: Run custom-user model tests
      run: uv run pytest tests_custom_user -p kwik.testing.fixtures -n 0

    - name: Type-check kernel typing contract
      run: uv run pyright tests_custom_user/test_typing_contract.py
```

- [ ] **Step 8: Lint, format, commit**

```bash
uv run ruff check && uv run ruff format
git add tests_custom_user/ pyproject.toml uv.lock .github/workflows/test.yml
git commit -S -m "test: custom-user session with pyright typing contract"
```

---

### Task 12: Documentation, spec sync, CHANGELOG, version 2.0.0

**Files:**
- Modify: `docs/handbook/docs/index.md`, `docs/handbook/docs/writing-endpoints.md`, `docs/handbook/docs/autocrud.md`, `docs/handbook/docs/testing.md`, `docs/handbook/docs/testing-fixtures.md` (sweep + quickstart)
- Create: `docs/handbook/docs/user-model.md`
- Modify: `docs/handbook/mkdocs.yml` (nav)
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-02-user-model-extensibility-design.md` (sync deviations)
- Modify: `CHANGELOG.md`, `pyproject.toml` (version)

**Interfaces:** documentation only; no code.

- [ ] **Step 1: Create `docs/handbook/docs/user-model.md`**

Full page with these sections (write complete prose around the code blocks):

1. **"Extending the User model"** — why: single `users` table, no 1:1 side tables or proxying.
2. **Composing a custom model:**

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from kwik.models import Base, UserMixin


class AppUser(Base, UserMixin):
    __tablename__ = "users"  # required: kwik's foreign keys reference this table

    company: Mapped[str] = mapped_column(String, default="", nullable=False)
    external: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

3. **Registering the kernel + typed aliases** (create it early, before router modules):

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

CurrentUser = Annotated[AppUser, Depends(kernel.get_current_user)]
UserContext = Annotated[Context[AppUser], Depends(kernel.get_user_context)]
```

4. **Building the app:**

```python
api_router = kernel.create_api_router()  # login/users/roles/permissions, each opt-out-able
api_router.include_router(my_router)

app = kwik.Kwik(settings=Settings(), api_router=api_router)
```

5. **Schemas contract** — profile needs `from_attributes`; registration must include the base fields plus a `password` field; custom fields flow into custom columns via `model_dump()`.
6. **Seeding** — `kwik.seeding.create_first_superuser(session=..., settings=..., **extra_fields)` from your `seed_db` hook.
7. **Testing** — conftest registers the kernel before fixtures; `UserSpec.extra_fields`; one kernel per process (run custom-model suites as separate pytest sessions).
8. **Migration from the 1.x two-table pattern** — checklist: define `AppUser(Base, UserMixin)` with the side-table's columns/relationships; create the kernel + aliases; one Alembic migration (add columns to `users`, rewrite side-table-id FKs to `users.id`, drop the side table); delete the side model/hybrids/translation dependencies; switch router assembly to `kernel.create_api_router()`; replace `crud_users` imports with `kernel.crud_users`; call the seeding battery.
9. **Zero-config apps** — nothing to do: `DefaultUser` + stock schemas materialize lazily.

- [ ] **Step 2: Update the rest of the handbook + README**

- `mkdocs.yml` nav, under `Introduction`: add `- User model: user-model.md` after `AutoCRUD`.
- Sweep: `grep -rn "api_router\|crud_users\|from kwik.models import User" docs/handbook/docs/ README.md` — update every hit: app assembly examples become `kernel.create_api_router()`; `crud_users` becomes `kernel.crud_users`; fix the incorrect `AutoCRUD` positional-arg example in `index.md` (AutoCRUD subclasses take no constructor args; the model comes from the generic parameters — show `class CustomerCRUD(AutoCRUD[UserCtx, Customer, CustomerCreate, CustomerUpdate, int]): ...` then `crud_customers = CustomerCRUD()`).
- README lines ~106-107: update the endpoint example to reference `kernel.crud_users` (or a plain AutoCRUD singleton for a non-user model — keep it minimal and correct).

- [ ] **Step 3: Sync the spec**

In `docs/superpowers/specs/2026-07-02-user-model-extensibility-design.md`:
- Replace both `tests/custom_user/` references with `tests_custom_user/` and add the rationale "(repo root, outside testpaths — the main suite must never collect it)".
- In the Kernel API sketch, remove the `get_maybe_user_context` line (dropped — YAGNI).

- [ ] **Step 4: CHANGELOG + version**

- `pyproject.toml`: `version = "2.0.0"`, then run `uv sync`.
- `CHANGELOG.md`: add a `## [2.0.0] - 2026-XX-XX` section (date of the release commit) at the top of the version list, matching the file's existing format, with subsections:
  - **Added**: `Kernel`/`UserSchemas`/`get_kernel`; `UserMixin` auth mixin; `DefaultUser`; kernel-bound router factories with per-router opt-out; `kwik.seeding.create_first_superuser`; `Scenario`/`user_factory` `extra_fields`; `ScenarioResult.passwords` + `IdentityAwareTestClient.register_passwords`; `AutoCRUD(model=...)`; custom-user test session + pyright typing contract.
  - **Changed**: `Context[U]` bounded by `UserMixin | None`; `current_user`/`resolved_user` typed `UserMixin`; audit-trail validation accepts any non-optional-user Context.
  - **Removed (BREAKING)**: `kwik.api_router` and `kwik.api.api`; module-level `users_router`/`login_router`/`roles_router`; `kwik.crud.crud_users` singleton; `kwik.models.User` export; audit `UserMixin` renamed `UserTrackingMixin`.
  - **Migration**: link to the handbook `user-model.md` guide.

- [ ] **Step 5: Final verification and commit**

Run: `uv run pytest && uv run pytest tests_custom_user -p kwik.testing.fixtures -n 0 && uv run pyright tests_custom_user/test_typing_contract.py && uv run ruff check && uv run ruff format`
Expected: everything green.

```bash
git add -A
git commit -S -m "docs: kwik 2.0 user-model extensibility guide, changelog, version 2.0.0"
```

---

## Plan Self-Review Notes

- **Spec coverage:** model layer (§1 → Tasks 1/2/6), kernel + registry (§2/§3 → Tasks 5/9), CRUD (§4 → Tasks 3/4), Context (§5 → Task 3), dependencies/security (§6 → Task 7), router factories (§7 → Task 9), 2.0 surface + seeding + settings + docs (§8 → Tasks 9/12), testing framework (§9 → Tasks 8/11), error handling (§10 → Task 5), migration guide (→ Task 12), acceptance criteria (→ Tasks 5–12). Spec deviations (tests_custom_user path, dropped `get_maybe_user_context`) are declared in Global Constraints and synced back in Task 12.
- **Known-risk steps (verify at execution, adjust minimally):** (a) SQLAlchemy accepting the unannotated dynamic `relationship(_user_model, ...)` assignments — if declarative requires an annotation, use `Mapped["DefaultUser"]`-free `declared_attr` form instead and re-run the suite; (b) pyright's handling of `TYPE_CHECKING` imports in the contract file (explicit fallback documented in Task 11 Step 4); (c) ruff rule codes (FA100/FA102, PLR0915, PLC0415, PLW0603, PLC2701) — if a listed noqa doesn't match the fired rule, use the code ruff actually reports; the intent (suppress that specific, justified violation) is what matters.
- **Type consistency:** `CRUDUsers[UserT: UserMixin]` constructed only via `CRUDUsers(model=...)`; `Kernel.crud_users: CRUDUsers[UserT]`; dependency methods return `UserT`/`Context[UserT]`; kwik-level aliases are `UserMixin`-typed. Names used across tasks: `get_kernel`, `_reset_for_testing`, `_active_kernel`, `create_first_superuser`, `ADMIN_ROLE_NAME`, `register_passwords`, `extra_fields`, `create_api_router(login=, users=, roles=, permissions=)`.

## Execution Handoff

Plan complete. Execute task-by-task with fresh reviews between tasks; every task ends with the full suite green and a signed commit.

