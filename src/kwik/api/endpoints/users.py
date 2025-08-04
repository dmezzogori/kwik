"""User management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kwik.typings
from kwik.api.deps import Pagination, current_user, has_permission
from kwik.core.enum import Permissions
from kwik.crud import users
from kwik.exceptions import DuplicatedEntity, Forbidden
from kwik.routers import AuditorRouter
from kwik.schemas import Paginated, UserPasswordChange, UserProfile, UserProfileUpdate, UserRegistration

if TYPE_CHECKING:
    from kwik.models import User

router = AuditorRouter(prefix="/users")


@router.get(
    "/",
    response_model=Paginated[UserProfile],
    dependencies=(has_permission(Permissions.users_management_read),),
)
def read_users(pagination: Pagination) -> kwik.typings.PaginatedResponse[User]:
    """Retrieve users."""
    total, data = users.get_multi(**pagination)
    return kwik.typings.PaginatedResponse(data=data, total=total)


@router.get("/me", response_model=UserProfile)
def read_user_me(user: current_user) -> User:
    """Get current user."""
    return user


@router.get("/{user_id}", response_model=UserProfile)
def read_user_by_id(user_id: int, user: current_user) -> User:
    """
    Get a specific user by id.

    If the user requested is not the same as the logged-in user, the user must have the user_management_read permission.
    """
    if user_id != user.id and not users.has_permissions(
        user_id=user.id,
        permissions=(Permissions.users_management_read,),
    ):
        raise Forbidden

    return user


@router.post(
    "/",
    response_model=UserProfile,
    dependencies=(has_permission(Permissions.users_management_create),),
)
def create_user(user_in: UserRegistration) -> User:
    """Create new user."""
    user = users.get_by_email(email=user_in.email)
    if user:
        raise DuplicatedEntity

    return users.create(obj_in=user_in)


@router.put("/me", response_model=UserProfile)
def update_myself(user: current_user, user_in: UserProfileUpdate) -> User:
    """Update details of the logged in user."""
    return users.update(db_obj=user, obj_in=user_in)


@router.put(
    "/{user_id}",
    response_model=UserProfile,
    dependencies=(has_permission(Permissions.users_management_update),),
)
def update_user(user_id: int, user_in: UserProfileUpdate) -> User:
    """Update a user."""
    user = users.get_if_exist(id=user_id)
    return users.update(db_obj=user, obj_in=user_in)


@router.put(
    "/{user_id}/update_password",
    response_model=UserProfile,
    dependencies=(has_permission(Permissions.users_management_update),),
)
def update_password(
    user_id: int,
    user: current_user,
    obj_in: UserPasswordChange,
) -> User:
    """
    Update the provided user's password.

    If the user is not the same as the logged-in user, the logged-in user must have the
    user_management_update permission.
    """
    if user_id != user.id and not users.has_permissions(
        user_id=user.id,
        permissions=(Permissions.users_management_update,),
    ):
        raise Forbidden

    return users.change_password(user_id=user_id, obj_in=obj_in)
