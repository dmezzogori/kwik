"""Token authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from kwik.core.security import decode_token
from kwik.schemas import TokenPayload

from .settings import Settings  # noqa: TC001


def _get_oauth2_scheme(settings: Settings) -> OAuth2PasswordBearer:
    token_url = f"{settings.API_V1_STR}/login/access-token"
    return OAuth2PasswordBearer(tokenUrl=token_url)


RawToken = Annotated[str, Depends(_get_oauth2_scheme)]


def get_token(raw_token: RawToken, settings: Settings) -> TokenPayload:
    """Get the decoded token payload."""
    return decode_token(token=raw_token, settings=settings)


current_token = Annotated[TokenPayload, Depends(get_token)]


__all__ = ["RawToken", "current_token", "get_token"]
