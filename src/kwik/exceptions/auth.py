"""Exception classes for bearer-token authentication and auth sessions."""

from __future__ import annotations

from fastapi import status

from .base import KwikError


class InvalidBearerTokenError(KwikError):
    """
    Exception raised when a bearer or refresh token is invalid, expired or revoked.

    The response carries the RFC 6750 challenge so clients know to refresh or sign in again.
    """

    def __init__(self, detail: str = "Invalid or expired token") -> None:
        """Initialize the invalid bearer token exception with a 401 status and the challenge header."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )


class SessionRevokedError(InvalidBearerTokenError):
    """
    Exception raised when a refresh revoked the session it was refused for.

    ``refresh_session`` raises it after ``store.revoke(...)``, on refresh-token reuse and for an
    impersonation session whose parent session is missing or inactive. The response is the same
    401 with the same challenge as :class:`InvalidBearerTokenError`. Under a ``Kwik`` app, kwik
    commits the request's database session before this error propagates (and only for this
    error), so a revocation a store wrote through that session is durable.
    """


class MissingBearerTokenError(KwikError):
    """Exception raised when a request that needs a bearer token carries none."""

    def __init__(self, detail: str = "Not authenticated") -> None:
        """Initialize the missing bearer token exception with a 401 status and the challenge header."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthSessionsNotConfiguredError(KwikError):
    """Exception raised when a session endpoint is called but the application configured no session store."""

    def __init__(self, detail: str = "Auth sessions are not configured") -> None:
        """Initialize the not-configured exception with a 501 status."""
        super().__init__(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)
