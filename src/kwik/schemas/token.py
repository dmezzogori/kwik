"""Schemas for authentication tokens."""

from pydantic import BaseModel


class Token(BaseModel):
    """Schema for authentication tokens with access token and type."""

    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Schema for JWT token payload data with user ID and impersonation info."""

    sub: int | None = None
    kwik_impersonate: str
