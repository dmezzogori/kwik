"""
Kwik dependency injection for application CRUD contexts.

This module provides dependency injection factories for creating CRUD context objects
that encapsulate database sessions and user information for request handling.

Exports:
- NoUserContext: CRUD context dependency for unauthenticated requests
- UserContext: CRUD context dependency for authenticated requests
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from kwik.crud.context import Context, NoUserCtx, UserCtx

from .session import Session  # noqa: TC001
from .users import current_user  # noqa: TC001


def _get_no_user_context(session: Session) -> NoUserCtx:
    """Get a context for a user that is not logged in."""
    return Context(session=session, user=None)


def _get_user_context(session: Session, user: current_user) -> UserCtx:
    """Get a context for a logged-in user."""
    return Context(session=session, user=user)


NoUserContext = Annotated[NoUserCtx, Depends(_get_no_user_context)]
UserContext = Annotated[UserCtx, Depends(_get_user_context)]


__all__ = ["NoUserContext", "UserContext"]
