"""Token authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

import kwik.core.security
import kwik.schemas
from kwik.core.settings import get_settings

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{get_settings().API_V1_STR}/login/access-token")


def get_token(token: str = Depends(reusable_oauth2)) -> kwik.schemas.TokenPayload:
    """
    Get the decoded token payload.

    Raises:
        Forbidden: if the token is invalid

    """
    return kwik.core.security.decode_token(token)


current_token = Annotated[kwik.schemas.TokenPayload, Depends(get_token)]
