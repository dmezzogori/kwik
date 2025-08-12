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

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models import User


@dataclass(slots=True, frozen=True)
class Context[U: (None, User, User | None)]:
    """
    A context object that holds database session and user information meant to be used at the CRUD layer level.

    This generic class provides a way to pass both database session and user
    context through the application. The user type parameter allows for
    different authentication states.

    Parameters
    ----------
    U : type
        The user type, constrained to None, User, or User | None to represent
        different authentication states.

    Attributes
    ----------
    session : Session
        The SQLAlchemy database session.
    user : U
        The user object, which can be None, User, or User | None depending
        on the authentication state.

    """

    session: Session
    user: U


type UserCtx = Context[User]
type MaybeUserCtx = Context[User | None]
type NoUserCtx = Context[None]
