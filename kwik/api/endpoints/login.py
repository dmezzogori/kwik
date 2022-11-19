from fastapi import Body, Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordRequestForm

import kwik
from kwik import crud, models, schemas
from kwik.api.deps import reusable_oauth2
from kwik.core.enum import PermissionNames
from kwik.core.security import decode_token, create_token
from kwik.exceptions import IncorrectCredentials, UserInactive, UserNotFound, NotFound
from kwik.schemas.login import RecoverPassword
from kwik.utils import (
    generate_password_reset_token,
    send_reset_password_email,
    verify_password_reset_token,
)

router = APIRouter()


@router.post("/access-token", response_model=schemas.Token)
def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    try:
        user = crud.user.authenticate(email=form_data.username, password=form_data.password)
        return create_token(user_id=user.id)
    except (IncorrectCredentials, UserInactive) as e:
        raise e.http_exc


@router.post(
    "/impersonate",
    response_model=schemas.Token,
    dependencies=[kwik.has_permission(PermissionNames.impersonification)],
)
def impersonate(user_id: int, current_user: models.User = kwik.current_user):
    try:
        user = crud.user.get_if_exist(id=user_id)
        return create_token(user_id=user.id, impersonator_user_id=current_user.id)
    except NotFound as e:
        raise e.http_exc


@router.post("/is_impersonating", response_model=bool)
def is_impersonating(token: str = Depends(reusable_oauth2)) -> bool:
    token_data = decode_token(token)
    return token_data.kwik_impersonate != ""


@router.post("/stop_impersonating", response_model=schemas.Token)
def stop_impersonating(token: str = Depends(reusable_oauth2)):
    token_data = decode_token(token)
    original_user_id = int(token_data.kwik_impersonate)
    return create_token(user_id=original_user_id)


@router.post("/test-token", response_model=schemas.User)
def test_token(current_user: models.User = kwik.current_user) -> models.User:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery", response_model=schemas.Msg)
def recover_password(obj_in: RecoverPassword) -> dict:
    """
    Password Recovery
    """
    email = obj_in.email
    user = crud.user.get_by_email(email=email)

    if not user:
        raise UserNotFound().http_exc
    password_reset_token = generate_password_reset_token(email=email)
    send_reset_password_email(email_to=user.email, email=email, token=password_reset_token)
    return {"msg": "Password recovery email sent"}


@router.post("/reset-password", response_model=schemas.Msg)
def reset_password(token: str = Body(...), password: str = Body(...)) -> dict:
    """
    Reset password
    """
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    try:
        crud.user.reset_password(email=email, password=password)
        return {"msg": "Password updated successfully"}
    except (UserNotFound, UserInactive) as e:
        raise e.http_exc
