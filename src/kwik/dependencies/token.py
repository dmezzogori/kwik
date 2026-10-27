"""
Bearer-token authentication dependencies for FastAPI endpoints.

The token comes from an ``Authorization: Bearer`` header through ``HTTPBearer``, so the
OpenAPI document declares one HTTP bearer scheme. When the application configured an
:class:`~kwik.auth.AuthSessionStore`, every authenticated request also checks that the
token's session is still active.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kwik.auth import AuthSessionStore, require_active_session
from kwik.exceptions.auth import InvalidBearerTokenError, MissingBearerTokenError
from kwik.exceptions.base import TokenValidationError
from kwik.schemas import TokenPayload
from kwik.security import decode_token

from .settings import Settings  # noqa: TC001

if TYPE_CHECKING:
    from kwik.settings import BaseKwikSettings

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearer")


def _get_auth_session_store(request: Request) -> AuthSessionStore | None:
    """
    Return the application's auth session store, or None when it configured none.

    Applications whose store needs the request's database session override this dependency.
    """
    return getattr(request.app.state, "auth_session_store", None)


AuthSessions = Annotated[AuthSessionStore | None, Depends(_get_auth_session_store)]


def _bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str | None:
    """Return the raw bearer token, or None when the header is missing or not a Bearer credential."""
    return None if credentials is None else credentials.credentials


def _payload_from(raw_token: str | None, settings: BaseKwikSettings, store: AuthSessionStore | None) -> TokenPayload:
    """
    Decode a raw bearer token and check its auth session.

    Raises:
        MissingBearerTokenError: If there is no bearer token.
        InvalidBearerTokenError: If the token is invalid or expired, or its session is not active.

    """
    if raw_token is None:
        raise MissingBearerTokenError
    try:
        payload = decode_token(token=raw_token, settings=settings)
    except TokenValidationError:
        raise InvalidBearerTokenError from None
    require_active_session(payload=payload, store=store)
    return payload


def get_token(
    raw_token: Annotated[str | None, Depends(_bearer_token)],
    settings: Settings,
    store: AuthSessions,
) -> TokenPayload:
    """Get the decoded payload of the request's bearer token, after the auth-session check."""
    return _payload_from(raw_token, settings, store)


current_token = Annotated[TokenPayload, Depends(get_token)]


__all__ = ["AuthSessions", "bearer_scheme", "current_token", "get_token"]
