"""Token authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from kwik.core.security import decode_token
from kwik.core.settings import get_settings
from kwik.schemas import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{get_settings().API_V1_STR}/login/access-token")


def get_token(token: str = Depends(reusable_oauth2)) -> TokenPayload:
    """Get the decoded token payload."""
    return decode_token(token)


current_token = Annotated[TokenPayload, Depends(get_token)]


__all__ = ["current_token", "get_token"]
