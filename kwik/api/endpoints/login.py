from __future__ import annotations

import kwik.api.deps
import kwik.core.enum
import kwik.core.security
import kwik.crud
import kwik.models
import kwik.schemas
import kwik.typings
import kwik.utils
from fastapi import APIRouter, Body, Depends
from fastapi.security import OAuth2PasswordRequestForm
from kwik.exceptions.base import InvalidToken

router = APIRouter()


@router.post("/access-token", response_model=kwik.typings.Token)
def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> kwik.typings.Token:
    """
    OAuth2 compatible token login, get an access token for future requests

    Raises:
        IncorrectCredentials: If the provided credentials are incorrect
    """

    user = kwik.crud.user.authenticate(email=form_data.username, password=form_data.password)
    return kwik.core.security.create_token(user_id=user.id)


@router.post("/test-token", response_model=kwik.schemas.UserORMSchema)
def test_token(current_user: kwik.api.deps.current_user) -> kwik.models.User:
    """
    Test access token
    """

    return current_user


@router.post(
    "/impersonate",
    response_model=kwik.typings.Token,
    dependencies=(kwik.api.deps.has_permission(kwik.core.enum.Permissions.impersonification),),
)
def impersonate(user_id: int, current_user: kwik.api.deps.current_user):
    """
    Impersonate a user.

    Permissions:
        * `impersonification`

    Raises:
        NotFound: If the provided user does not exist
    """

    # Retrieve the user to impersonate
    user = kwik.crud.user.get_if_exist(id=user_id)

    return kwik.core.security.create_token(user_id=user.id, impersonator_user_id=current_user.id)


@router.post("/is_impersonating", response_model=bool)
def is_impersonating(token: str = Depends(kwik.api.deps.token.reusable_oauth2)) -> bool:
    """
    Check if the current token is impersonating another user

    Raises:
        InvalidToken: If the token is invalid
    """

    token_data = kwik.core.security.decode_token(token)
    return token_data.kwik_impersonate != ""


@router.post("/stop_impersonating", response_model=kwik.typings.Token)
def stop_impersonating(token: str = Depends(kwik.api.deps.token.reusable_oauth2)):
    """
    Stop impersonating and return the original token

    Raises:
        InvalidToken: If the token is invalid
    """

    token_data = kwik.core.security.decode_token(token)
    original_user_id = int(token_data.kwik_impersonate)
    return kwik.core.security.create_token(user_id=original_user_id)


@router.post("/reset-password", response_model=kwik.schemas.Msg)
def reset_password(token: str = Body(...), password: str = Body(...)) -> dict:
    """
    Reset password
    """

    email = kwik.utils.verify_password_reset_token(token)
    if not email:
        raise InvalidToken

    kwik.crud.user.reset_password(email=email, password=password)
    return {"msg": "Password updated successfully"}
