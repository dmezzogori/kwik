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
