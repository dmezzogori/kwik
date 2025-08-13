"""Token authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from kwik.schemas import TokenPayload
from kwik.security import decode_token
from kwik.settings import BaseKwikSettings

from .settings import Settings  # noqa: TC001

settings = BaseKwikSettings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")


def get_token(raw_token: Annotated[str, Depends(oauth2_scheme)], settings: Settings) -> TokenPayload:
    """Get the decoded token payload."""
    return decode_token(token=raw_token, settings=settings)


current_token = Annotated[TokenPayload, Depends(get_token)]


__all__ = ["current_token", "get_token"]
