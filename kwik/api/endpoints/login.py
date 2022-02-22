from typing import Any

from fastapi import Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import kwik
from kwik import crud, models, schemas
from kwik.api.deps import reusable_oauth2
from kwik.core.enum import PermissionNames
from kwik.core.security import get_password_hash, decode_token, create_token
from kwik.routers import AuditorRouter
from kwik.utils import (
    generate_password_reset_token,
    send_reset_password_email,
    verify_password_reset_token,
)

router = AuditorRouter()


@router.post("/login/access-token", response_model=schemas.Token)
def login_access_token(db: Session = kwik.db, form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.user.authenticate(db=db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return create_token(user_id=user.id)


@router.post(
    "/login/impersonate",
    response_model=schemas.Token,
    dependencies=[kwik.has_permission(PermissionNames.impersonification)],
)
def impersonate(user_id: int, db: Session = kwik.db, current_user: models.User = kwik.current_user):
    user = crud.user.get(db=db, id=user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")

    return create_token(user_id=user.id, impersonator_user_id=current_user.id)


@router.post("/login/is_impersonating", response_model=bool)
def is_impersonating(token: str = Depends(reusable_oauth2)):
    token_data = decode_token(token)
    return token_data.kwik_impersonate != ""


@router.post(
    "/login/stop_impersonating", response_model=schemas.Token,
)
def stop_impersonating(token: str = Depends(reusable_oauth2)):
    token_data = decode_token(token)
    original_user_id = int(token_data.kwik_impersonate)
    return create_token(user_id=original_user_id)


@router.post("/login/test-token", response_model=schemas.User)
def test_token(current_user: models.User = kwik.current_user) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}", response_model=schemas.Msg)
def recover_password(email: str, db: Session = kwik.db) -> Any:
    """
    Password Recovery
    """
    user = crud.user.get_by_email(db, email=email)

    if not user:
        raise HTTPException(
            status_code=404, detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    send_reset_password_email(email_to=user.email, email=email, token=password_reset_token)
    return {"msg": "Password recovery email sent"}


@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(token: str = Body(...), new_password: str = Body(...), db: Session = kwik.db,) -> Any:
    """
    Reset password
    """
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=404, detail="The user with this username does not exist in the system.",
        )
    elif not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.add(user)
    db.flush()
    return {"msg": "Password updated successfully"}
