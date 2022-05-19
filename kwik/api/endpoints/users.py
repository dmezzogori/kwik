from typing import Any

from fastapi import Body, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic.networks import EmailStr
from sqlalchemy.orm import Session

import kwik
from kwik.routers import AuditorRouter
from kwik.utils import send_new_account_email
from kwik import crud, models, schemas, PaginatedQuery, has_permission
from kwik.core.enum import PermissionNames


router = AuditorRouter()


@router.get(
    "/", response_model=schemas.Paginated[schemas.User], dependencies=[has_permission(PermissionNames.user_management)],
)
def read_users(db: Session = kwik.db, paginated=PaginatedQuery) -> Any:
    """
    Retrieve users.
    """
    count, users = crud.user.get_multi(db=db, **paginated)
    return {"data": users, "total": count}


@router.post(
    "/", response_model=schemas.User, dependencies=[kwik.has_permission(PermissionNames.user_management)],
)
def create_user(*, db: Session = kwik.db, user_in: schemas.UserCreate,) -> Any:
    """
    Create new user.
    """
    user = crud.user.get_by_email(db=db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400, detail="The user with this username already exists in the system.",
        )
    user = crud.user.create(db=db, obj_in=user_in)
    if kwik.settings.EMAILS_ENABLED and user_in.email:
        send_new_account_email(email_to=user_in.email, username=user_in.email, password=user_in.password)
    return user


@router.put("/me", response_model=schemas.User)
def update_user_me(
    *,
    db: Session = kwik.db,
    password: str = Body(None),
    full_name: str = Body(None),
    email: EmailStr = Body(None),
    current_user: models.User = kwik.current_active_user,
) -> Any:
    """
    Update own user.
    """
    current_user_data = jsonable_encoder(current_user)
    user_in = schemas.UserUpdate(**current_user_data)
    if password is not None:
        user_in.password = password
    if full_name is not None:
        user_in.full_name = full_name
    if email is not None:
        user_in.email = email
    user = crud.user.update(db=db, db_obj=current_user, obj_in=user_in)
    return user


@router.get("/me", response_model=schemas.UserWithPermissionsAndRoles)
def read_user_me(current_user: models.User = kwik.current_active_user,) -> Any:
    """
    Get current user.
    """
    return current_user


@router.post("/open", response_model=schemas.User)
def create_user_open(
    *, db: Session = kwik.db, password: str = Body(...), email: EmailStr = Body(...), full_name: str = Body(None),
) -> Any:
    """
    Create new user without the need to be logged in.
    """
    if not kwik.settings.USERS_OPEN_REGISTRATION:
        raise HTTPException(
            status_code=403, detail="Open user registration is forbidden on this server",
        )
    user = crud.user.get_by_email(db=db, email=email)
    if user:
        raise HTTPException(
            status_code=400, detail="The user with this username already exists in the system",
        )
    user_in = schemas.UserCreate(password=password, email=email, full_name=full_name)
    user = crud.user.create(db=db, obj_in=user_in)
    return user


@router.get("/{user_id}", response_model=schemas.User)
def read_user_by_id(user_id: int, current_user: models.User = kwik.current_active_user, db: Session = kwik.db,) -> Any:
    """
    Get a specific user by id.
    """
    user = crud.user.get(db=db, id=user_id)
    if user == current_user:
        return user
    if not crud.user.is_superuser(current_user):
        raise HTTPException(status_code=400, detail="The user doesn't have enough privileges")
    return user


@router.put("/{user_id}", response_model=schemas.User)
def update_user(*, db: Session = kwik.db, user_id: int, user_in: schemas.UserUpdate,) -> Any:
    """
    Update a user.
    """
    user = crud.user.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail="The user with this username does not exist in the system",
        )
    user = crud.user.update(db=db, db_obj=user, obj_in=user_in)
    return user


@router.put("/{user_id}/update_password", response_model=schemas.User)
def update_password(
    *,
    db: Session = kwik.db,
    user_id: int,
    obj_in: schemas.UserChangePassword,
    current_user: models.User = kwik.current_active_user,
) -> models.User:
    """
    Update the provided user's password.
    At the moment, it doesn't check that the current user is the one changing its own password because in the future
    a user's password could be forced by an user with adequate permissions.
    The old password is however required at the moment.
    The user still needs to be authenticated to change an user's password
    """
    user = crud.user.change_password(db=db, user_id=user_id, obj_in=obj_in)
    return user