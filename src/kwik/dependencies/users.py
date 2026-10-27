"""User authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from kwik.crud import crud_users
from kwik.crud.context import Context
from kwik.exceptions import AccessDeniedError
from kwik.models import User

from .session import Session  # noqa: TC001
from .settings import Settings  # noqa: TC001
from .token import AuthSessions, _bearer_token, _payload_from, current_token


def _get_current_user(token: current_token, session: Session) -> User:
    """
    Get the user associated with the token.

    Raises:
        Forbidden: if the user is not found

    """
    if token.sub is None:
        raise AccessDeniedError

    context = Context(session=session, user=None)
    user = crud_users.get(entity_id=token.sub, context=context)
    if user is None:
        raise AccessDeniedError

    return user


def _resolve_current_user(
    request: Request,
    raw_token: Annotated[str | None, Depends(_bearer_token)],
    settings: Settings,
    session: Session,
    store: AuthSessions,
) -> User:
    """
    Resolve the current user from either an API key or a bearer token.

    Checks ``request.state.api_key_user`` first (set by
    ``verify_api_key`` on ``ApiKeyRouter``). Falls back to the bearer
    token, whose auth session is checked when the application configured
    a store. This allows ``has_permission`` to work transparently on both
    ``AuthenticatedRouter`` and ``ApiKeyRouter``.

    ``store`` has no default on purpose: a direct caller that omitted it
    would silently skip the auth-session check.

    Args:
        request: The incoming HTTP request.
        raw_token: Optional bearer token (None when the header is missing).
        settings: Application settings for token decoding.
        session: Database session.
        store: The application's auth session store, or None.

    Returns:
        The authenticated user.

    Raises:
        MissingBearerTokenError: 401 if neither an API key user nor a bearer token is present.
        InvalidBearerTokenError: 401 if the token is invalid or expired, or its session is not active.
        AccessDeniedError: 403 if the user is not found in the database.

    """
    # API key path — user already resolved by verify_api_key
    user = getattr(request.state, "api_key_user", None)
    if user is not None:
        return user

    # Bearer path
    token = _payload_from(raw_token, settings, store)
    if token.sub is None:
        raise AccessDeniedError

    context = Context(session=session, user=None)
    user = crud_users.get(entity_id=token.sub, context=context)
    if user is None:
        raise AccessDeniedError

    return user


current_user = Annotated[User, Depends(_get_current_user)]
resolved_user = Annotated[User, Depends(_resolve_current_user)]

__all__ = ["current_user", "resolved_user"]
