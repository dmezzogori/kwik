"""
Typed kernel: the single registration point for the application's user model and schemas.

A consuming application constructs exactly one ``Kernel`` — before importing kwik
routers or running the app. kwik internals resolve the active kernel via
``get_kernel()``, which materializes a default kernel wired to ``DefaultUser``
for zero-config applications.

This module must not use ``from __future__ import annotations``: FastAPI-facing
signatures added here must evaluate eagerly.
"""

import sys
from dataclasses import dataclass
from typing import Annotated, Final, cast

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import inspect

from kwik.crud.context import Context
from kwik.crud.users import CRUDUsers
from kwik.dependencies.session import Session
from kwik.dependencies.users import _get_current_user, _resolve_current_user
from kwik.models.base import Base
from kwik.models.user_mixin import UserMixin
from kwik.routers import AuthenticatedRouter
from kwik.schemas import UserProfile, UserProfileUpdate, UserRegistration

_REQUIRED_COLUMNS: Final[frozenset[str]] = frozenset({"id", "name", "surname", "email", "hashed_password", "is_active"})


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
    """Enforce the schema contract on the resolved bundle; runs BEFORE the slot is claimed."""
    for field_name in ("profile", "registration", "update"):
        schema = getattr(schemas, field_name)
        if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
            msg = f"UserSchemas.{field_name} must be a Pydantic BaseModel subclass (got {schema!r})"
            raise TypeError(msg)
    if not schemas.profile.model_config.get("from_attributes", False):
        msg = "UserSchemas.profile must enable model_config['from_attributes'] to serialize ORM objects"
        raise TypeError(msg)
    registration_fields = set(schemas.registration.model_fields)
    if "password" not in registration_fields:
        msg = "registration schema must declare a 'password' field"
        raise TypeError(msg)
    forbidden = {"hashed_password", "id"} & registration_fields
    if forbidden:
        msg = "registration schema must not expose 'hashed_password'/'id' — these are managed by kwik"
        raise TypeError(msg)


class Kernel[UserT: UserMixin]:
    """Process-wide registration of the application's user model and schemas."""

    user_model: type[UserT]
    schemas: UserSchemas
    crud_users: CRUDUsers[UserT]

    def __init__(self, *, user_model: type[UserT], schemas: UserSchemas | None = None) -> None:
        """Validate the model and schemas, build crud_users, then claim the process-wide slot last."""
        _validate_user_model(user_model)
        resolved_schemas = (
            schemas
            if schemas is not None
            else UserSchemas(profile=UserProfile, registration=UserRegistration, update=UserProfileUpdate)
        )
        _validate_schemas(resolved_schemas)
        self.user_model = user_model
        self.schemas = resolved_schemas
        self.crud_users = CRUDUsers(model=user_model)
        # Claim the slot LAST: if validation or CRUDUsers construction raises above, the
        # process-wide slot stays free instead of being poisoned by a half-built kernel.
        _claim_slot(self)

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
    if kernel is not None:
        return kernel
    return _materialize_default_kernel()


def _materialize_default_kernel() -> Kernel[UserMixin]:
    """
    Build the zero-config DefaultUser kernel, guarding two edge cases.

    Forgotten kernel: if a custom user model already mapped the ``users`` table but no
    Kernel was constructed, importing DefaultUser would collide on that table — raise an
    actionable error instead of a cryptic SQLAlchemy one. Benign race: if another thread
    claimed the slot while we were constructing, return the kernel it registered.
    """
    if "users" in Base.metadata.tables and "kwik.models.default_user" not in sys.modules:
        msg = (
            "a custom user model is mapped but no Kernel was constructed — build "
            "Kernel(user_model=...) before importing kwik routers or running the app"
        )
        raise RuntimeError(msg)

    # Lazy import: DefaultUser is mapped only when actually needed, so a custom
    # user model never collides with it in Base.metadata.
    from kwik.models.default_user import DefaultUser  # noqa: PLC0415

    try:
        return Kernel(user_model=DefaultUser)
    except RuntimeError:
        # Another thread won the slot between our guard check and _claim_slot; reuse its kernel.
        recovered = _active_kernel
        if recovered is not None:
            return recovered
        raise


def _reset_for_testing() -> None:
    """Clear the kernel slot. Test-only; models already mapped by the outgoing kernel stay mapped."""
    global _active_kernel  # noqa: PLW0603
    _active_kernel = None


__all__ = ["Kernel", "UserSchemas", "get_kernel"]
