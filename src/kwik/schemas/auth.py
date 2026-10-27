"""Schemas for the auth session endpoints."""

from pydantic import BaseModel


class RefreshRequest(BaseModel):
    """Request body of ``POST /login/refresh``: the refresh token to exchange."""

    refresh_token: str
