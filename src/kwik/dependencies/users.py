"""User authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from kwik.crud import crud_users
from kwik.crud.context import Context
from kwik.exceptions import AccessDeniedError
from kwik.models import User
from kwik.security import decode_token

from .session import Session  # noqa: TC001
from .settings import Settings  # noqa: TC001
from .token import current_token  # noqa: TC001

# Optional OAuth2 scheme that does NOT raise on missing Bearer token.
# Used by _resolve_current_user to support both JWT and API key auth.
_settings = __import__("kwik.settings", fromlist=["BaseKwikSettings"]).BaseKwikSettings()
_oauth2_optional = OAuth2PasswordBearer(
    tokenUrl=f"{_settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


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
    raw_token: Annotated[str | None, Depends(_oauth2_optional)],
    settings: Settings,
    session: Session,
) -> User:
    """
    Resolve the current user from either an API key or a JWT.

    Checks ``request.state.api_key_user`` first (set by
    ``verify_api_key`` on ``ApiKeyRouter``). Falls back to decoding
    the JWT Bearer token. This allows ``has_permission`` to work
    transparently on both ``AuthenticatedRouter`` and ``ApiKeyRouter``.

    Args:
        request: The incoming HTTP request.
        raw_token: Optional Bearer token (extracted with ``auto_error=False``).
        settings: Application settings for JWT decoding.
        session: Database session.

    Returns:
        The authenticated user.

    Raises:
        HTTPException: 401 if no user can be resolved from either source.
        AccessDeniedError: 403 if the user is not found in the database.

    """
    # API key path — user already resolved by verify_api_key
    user = getattr(request.state, "api_key_user", None)
    if user is not None:
        return user

    # JWT path
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = decode_token(token=raw_token, settings=settings)
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
