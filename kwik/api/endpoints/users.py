import kwik
from fastapi import Body, HTTPException
from fastapi.encoders import jsonable_encoder
from kwik import crud, models, schemas, PaginatedQuery, has_permission
from kwik.core.enum import PermissionNames
from kwik.exceptions import DuplicatedEntity, NotFound
from kwik.routers import AuditorRouter
from kwik.utils import send_new_account_email
from pydantic.networks import EmailStr

router = AuditorRouter()


@router.get(
    "/",
    response_model=schemas.Paginated[schemas.User],
    dependencies=[has_permission(PermissionNames.user_management)],
)
def read_users(paginated=PaginatedQuery):
    """
    Retrieve users.
    """
    count, users = crud.user.get_multi(**paginated)
    return {"data": users, "total": count}


@router.post(
    "/",
    response_model=schemas.User,
    dependencies=[kwik.has_permission(PermissionNames.user_management)],
)
def create_user(
    user_in: schemas.UserCreate,
) -> models.User:
    """
    Create new user.
    """
    user = crud.user.get_by_email(email=user_in.email)
    if user:
        raise DuplicatedEntity().http_exc
    user = crud.user.create(obj_in=user_in)
    if kwik.settings.EMAILS_ENABLED and user_in.email:
        send_new_account_email(email_to=user_in.email, username=user_in.email, password=user_in.password)
    return user


@router.put("/me", response_model=schemas.User)
def update_user_me(
    password: str = Body(None),
    full_name: str = Body(None),
    email: EmailStr = Body(None),
    user: models.User = kwik.current_user,
) -> models.User:
    """
    Update own user.
    """
    current_user_data = jsonable_encoder(user)
    user_in = schemas.UserUpdate(**current_user_data)
    if password is not None:
        user_in.password = password
    if full_name is not None:
        user_in.full_name = full_name
    if email is not None:
        user_in.email = email
    user = crud.user.update(db_obj=user, obj_in=user_in)
    return user


@router.get("/me", response_model=schemas.UserWithPermissionsAndRoles)
def read_user_me(user: models.User = kwik.current_user) -> models.User:
    """
    Get current user.
    """
    return user


@router.post("/open", response_model=schemas.User)
def create_user_open(
    password: str = Body(...),
    email: EmailStr = Body(...),
    full_name: str = Body(None),
) -> models.User:
    """
    Create new user without the need to be logged in.
    """
    if not kwik.settings.USERS_OPEN_REGISTRATION:
        raise HTTPException(
            status_code=403,
            detail="Open user registration is forbidden on this server",
        )
    user = crud.user.get_by_email(email=email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    user_in = schemas.UserCreate(password=password, email=email, full_name=full_name)
    user = crud.user.create(obj_in=user_in)
    return user


@router.get("/{user_id}", response_model=schemas.User)
def read_user_by_id(
    user_id: int,
    user: models.User = kwik.current_user,
) -> models.User:
    """
    Get a specific user by id.
    """
    user_db = crud.user.get(id=user_id)
    if user_db == user:
        return user_db
    if not crud.user.is_superuser(user_id=user.id):
        raise HTTPException(status_code=400, detail="The user doesn't have enough privileges")
    return user_db


@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
) -> models.User:
    """
    Update a user.
    """
    try:
        user = crud.user.get_if_exist(id=user_id)
        user = crud.user.update(db_obj=user, obj_in=user_in)
        return user
    except NotFound as e:
        raise e.http_exc


@router.put("/{user_id}/update_password", response_model=schemas.User)
def update_password(
    user_id: int,
    obj_in: schemas.UserChangePassword,
    user: models.User = kwik.current_user,
) -> models.User:
    """
    Update the provided user's password.
    At the moment, it doesn't check that the current user is the one changing its own password because in the future
    a user's password could be forced by an user with adequate permissions.
    The old password is however required at the moment.
    The user still needs to be authenticated to change an user's password
    """
    return crud.user.change_password(user_id=user_id, obj_in=obj_in)
