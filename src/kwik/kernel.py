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
