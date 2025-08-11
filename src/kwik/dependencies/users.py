"""User authentication dependencies for FastAPI endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from kwik.crud import crud_users
from kwik.exceptions import AccessDeniedError
from kwik.models import User

from .token import current_token  # noqa: TC001


def _get_current_user(token: current_token) -> User:
    """
    Get the user associated with the token.

    Raises:
        Forbidden: if the user is not found

    """
    user = crud_users.get(id=token.sub)
    if user is None:
        raise AccessDeniedError

    return user


current_user = Annotated[User, Depends(_get_current_user)]

__all__ = ["current_user"]
