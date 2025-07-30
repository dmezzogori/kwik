"""User authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

import kwik.crud
import kwik.exceptions
import kwik.models

from .token import current_token  # noqa: TC001


def get_current_user(token: current_token) -> kwik.models.User:
    """Get the user associated with the token.

    Raises:
        Forbidden: if the user is not found

    """
    user = kwik.crud.user.get(id=token.sub)
    if user is None:
        raise kwik.exceptions.Forbidden

    return user


current_user = Annotated[kwik.models.User, Depends(get_current_user)]
