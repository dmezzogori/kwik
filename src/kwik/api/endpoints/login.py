"""Authentication and login API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.security import OAuth2PasswordRequestForm  # noqa: TC002

from kwik.core.enum import Permissions
from kwik.core.security import create_token
from kwik.crud import crud_users
from kwik.dependencies import NoUserContext, UserContext, current_token, current_user, has_permission
from kwik.exceptions.base import TokenValidationError
from kwik.schemas import UserProfile
from kwik.typings import Token
from kwik.utils import verify_password_reset_token

if TYPE_CHECKING:
    from kwik.models import User

login_router = APIRouter(prefix="/login", tags=["login"])


@login_router.post("/access-token", response_model=Token)
def login_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], context: NoUserContext) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.

    Raises:
        IncorrectCredentials: If the provided credentials are incorrect

    """
    user = crud_users.authenticate(email=form_data.username, password=form_data.password, context=context)
    return create_token(user_id=user.id)


@login_router.post("/test-token", response_model=UserProfile)
def test_token(user: current_user) -> User:
    """Test access token."""
    return user


@login_router.post(
    "/impersonate",
    response_model=Token,
    dependencies=(has_permission(Permissions.impersonification),),
)
def impersonate(user_id: int, user: current_user, context: UserContext) -> Token:
    """Impersonate a user."""
    user_to_impersonate = crud_users.get_if_exist(id=user_id, context=context)
    return create_token(user_id=user_to_impersonate.id, impersonator_user_id=user.id)


@login_router.post("/is_impersonating", response_model=bool)
def is_impersonating(token: current_token) -> bool:
    return token.kwik_impersonate != ""


@login_router.post("/stop_impersonating", response_model=Token)
def stop_impersonating(token: current_token) -> Token:
    """
    Stop impersonating and return the original token.

    Raises:
        InvalidToken: If the token is invalid

    """
    original_user_id = int(token.kwik_impersonate)
    return create_token(user_id=original_user_id)


@login_router.post("/reset-password")
def reset_password(token: Annotated[str, Body()], password: Annotated[str, Body()], context: UserContext) -> dict:
    """Reset password."""
    email = verify_password_reset_token(token)
    if not email:
        raise TokenValidationError

    crud_users.reset_password(email=email, password=password, context=context)
    return {"msg": "Password updated successfully"}


__all__ = ["login_router"]
