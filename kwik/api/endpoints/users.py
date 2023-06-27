from __future__ import annotations

import kwik.api.deps
import kwik.crud
import kwik.models
import kwik.schemas
import kwik.typings
from kwik.core.enum import Permissions
from kwik.exceptions import DuplicatedEntity, Forbidden
from kwik.routers import AuditorRouter
from kwik.utils import send_new_account_email

router = AuditorRouter()


@router.get(
    "/",
    response_model=kwik.schemas.Paginated[kwik.schemas.UserORMSchema],
    dependencies=[kwik.api.deps.has_permission(Permissions.users_management_read)],
)
def read_users(paginated: kwik.api.deps.PaginatedQuery) -> kwik.typings.PaginatedResponse[kwik.models.User]:
    """
    Retrieve users.
    """

    total, data = kwik.crud.user.get_multi(**paginated)
    return kwik.typings.PaginatedResponse(data=data, total=total)


@router.get("/me", response_model=kwik.schemas.UserORMExtendedSchema)
def read_user_me(user: kwik.api.deps.current_user) -> kwik.models.User:
    """
    Get current user.
    """

    return user


@router.get(
    "/{user_id}",
    response_model=kwik.schemas.UserORMSchema,
)
def read_user_by_id(
    user_id: int,
    user: kwik.api.deps.current_user,
) -> kwik.models.User:
    """
    Get a specific user by id.
    If the user requested is not the same as the logged-in user, the user must have the user_management_read permission.
    """

    if user_id != user.id:
        if not kwik.crud.user.has_permissions(user_id=user.id, permissions=(Permissions.users_management_read,)):
            raise Forbidden

    return user


@router.post(
    "",
    response_model=kwik.schemas.UserORMSchema,
    dependencies=[kwik.api.deps.has_permission(Permissions.users_management_create)],
)
def create_user(user_in: kwik.schemas.UserCreateSchema) -> kwik.models.User:
    """
    Create new user.
    """

    user = kwik.crud.user.get_by_email(email=user_in.email)
    if user:
        raise DuplicatedEntity

    user = kwik.crud.user.create(obj_in=user_in)

    if kwik.settings.EMAILS_ENABLED:
        send_new_account_email(email_to=user_in.email, username=user_in.email, password=user_in.password)

    return user


@router.put("/me", response_model=kwik.schemas.UserORMSchema)
def update_myself(
    user: kwik.api.deps.current_user,
    user_in: kwik.schemas.UserUpdateSchema,
) -> kwik.models.User:
    """
    Update details of the logged in user.
    """

    return kwik.crud.user.update(db_obj=user, obj_in=user_in)


@router.put(
    "/{user_id}",
    response_model=kwik.schemas.UserORMSchema,
    dependencies=[kwik.api.deps.has_permission(Permissions.users_management_update)],
)
def update_user(
    user_id: int,
    user_in: kwik.schemas.UserUpdateSchema,
) -> kwik.models.User:
    """
    Update a user.
    """

    user = kwik.crud.user.get_if_exist(id=user_id)
    return kwik.crud.user.update(db_obj=user, obj_in=user_in)


@router.put(
    "/{user_id}/update_password",
    response_model=kwik.schemas.UserORMSchema,
    dependencies=[kwik.api.deps.has_permission(Permissions.users_management_update)],
)
def update_password(
    user_id: int,
    user: kwik.api.deps.current_user,
    obj_in: kwik.schemas.UserChangePasswordSchema,
) -> kwik.models.User:
    """
    Update the provided user's password.
    If the user is not the same as the logged-in user, the logged-in user must have the user_management_update permission.
    """

    if user_id != user.id:
        if not kwik.crud.user.has_permissions(user_id=user.id, permissions=(Permissions.users_management_update,)):
            raise Forbidden

    return kwik.crud.user.change_password(user_id=user_id, obj_in=obj_in)
