"""
API key authentication dependency for FastAPI.

Provides ``verify_api_key``, a FastAPI dependency that authenticates
requests via the ``X-API-Key`` HTTP header. The key is hashed with
SHA-256 and looked up in the ``api_keys`` table. On success, the
dependency returns a ``Context(session, user)`` identical to what
JWT-based authentication produces, so downstream CRUD code works
unchanged.

The resolved user is also stored on ``request.state.api_key_user``
so that shared dependencies like ``has_permission`` can resolve the
user without triggering the JWT dependency chain.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select

from kwik.crud.context import Context, UserCtx
from kwik.models.api_key import ApiKey
from kwik.models.user import User

from .session import Session  # noqa: TC001


def _verify_api_key(
    *,
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
    session: Session,
) -> UserCtx:
    """
    Validate an API key from the ``X-API-Key`` request header.

    Performs the following checks in order:

    1. Header is present.
    2. Key hash matches a row in ``api_keys``.
    3. Key is not revoked (``revoked_at`` is null).
    4. Key is not expired (``expires_at`` is null or in the future).
    5. Linked user is active.

    On success, updates ``last_used_at``, stores the resolved user on
    ``request.state.api_key_user``, and returns a
    ``Context(session, user)`` for use by downstream CRUD services.

    Args:
        request: The incoming HTTP request (used to store resolved user).
        x_api_key: Value of the ``X-API-Key`` HTTP header.
        session: Database session injected by FastAPI.

    Returns:
        Authenticated user context.

    Raises:
        HTTPException: 401 Unauthorized if any validation check fails.

    """
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    api_key = session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash)).scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if api_key.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked",
        )

    now = datetime.now()  # noqa: DTZ005
    if api_key.expires_at is not None and api_key.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    user = session.get(User, api_key.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key owner is inactive",
        )

    api_key.last_used_at = now
    session.flush()

    # Store user on request state so has_permission can resolve it
    # without triggering the JWT dependency chain.
    request.state.api_key_user = user

    return Context(session=session, user=user)


verify_api_key = _verify_api_key

ApiKeyContext = Annotated[UserCtx, Depends(_verify_api_key)]


__all__ = ["ApiKeyContext", "verify_api_key"]
