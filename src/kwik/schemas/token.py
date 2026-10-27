"""Schemas for authentication tokens."""

from typing import Literal

from pydantic import BaseModel


class Token(BaseModel):
    """
    Schema for the OAuth2 bearer token response.

    ``refresh_token`` and ``expires_in`` are filled only for session-aware tokens; a token
    minted without a session serialises both as ``null``.
    """

    access_token: str
    token_type: str
    refresh_token: str | None = None
    expires_in: int | None = None


class TokenPayload(BaseModel):
    """
    Schema for JWT token payload data.

    ``typ`` defaults to ``"access"`` so a token minted by kwik 1.13, which carries neither
    ``typ`` nor ``sid``, still validates.
    """

    sub: int | None = None
    kwik_impersonate: str
    sid: str | None = None
    typ: Literal["access", "refresh"] = "access"
    jti: str | None = None
