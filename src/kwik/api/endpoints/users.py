"""User management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.crud import crud_users
from kwik.dependencies import ListQuery, UserContext, current_user, has_permission
from kwik.exceptions import DuplicatedEntityError
from kwik.routers import AuthenticatedRouter
from kwik.schemas import (
    Paginated,
    PermissionProfile,
    RoleProfile,
    UserPasswordChange,
    UserProfile,
    UserProfileUpdate,
    UserRegistration,
)

if TYPE_CHECKING:
    from kwik.models import Permission, Role, User

users_router = AuthenticatedRouter(prefix="/users")


@users_router.get(
    "/",
    response_model=Paginated[UserProfile],
    dependencies=(has_permission(Permissions.users_management_read),),
)
def read_users(q: ListQuery, context: UserContext) -> Paginated[UserProfile]:
    """Retrieve users."""
    total, data = crud_users.get_multi(context=context, **q)
    return {"total": total, "data": data}


@users_router.post(
    "/",
    response_model=UserProfile,
    dependencies=(has_permission(Permissions.users_management_create),),
)
def create_user(user_in: UserRegistration, context: UserContext) -> User:
    """Create new user."""
    user = crud_users.get_by_email(email=user_in.email, context=context)
    if user:
        raise DuplicatedEntityError

    return crud_users.create(obj_in=user_in, context=context)


@users_router.get("/me", response_model=UserProfile)
def read_user_me(user: current_user) -> User:
    """Get current user."""
    return user


@users_router.put("/me", response_model=UserProfile)
def update_myself(user: current_user, user_in: UserProfileUpdate, context: UserContext) -> User:
    """Update details of the logged in user."""
    return crud_users.update(entity_id=user.id, obj_in=user_in, context=context)


@users_router.get("/me/permissions", response_model=list[PermissionProfile])
def read_permissions_of_current_user(user: current_user) -> list[Permission]:
    """Get all effective permissions of the current logged-in user."""
    return crud_users.get_permissions(user=user)


@users_router.get("/me/roles", response_model=list[RoleProfile])
def read_roles_of_current_user(user: current_user) -> list[Role]:
    """Get roles of the current logged-in user."""
    return crud_users.get_roles(user=user)


@users_router.put("/me/password", response_model=UserProfile)
def update_my_password(user: current_user, obj_in: UserPasswordChange, context: UserContext) -> User:
    """Update current user's password."""
    return crud_users.change_password(user_id=user.id, obj_in=obj_in, context=context)


@users_router.get(
    "/{user_id}",
    response_model=UserProfile,
    dependencies=(has_permission(Permissions.users_management_read),),
)
def read_user_by_id(user_id: int, context: UserContext) -> User:
    """Get a specific user by id."""
    return crud_users.get_if_exist(entity_id=user_id, context=context)


@users_router.put(
    "/{user_id}",
    response_model=UserProfile,
    dependencies=(has_permission(Permissions.users_management_update),),
)
def update_user(user_id: int, user_in: UserProfileUpdate, context: UserContext) -> User:
    """Update a user."""
    return crud_users.update(entity_id=user_id, obj_in=user_in, context=context)


@users_router.get(
    "/{user_id}/permissions",
    response_model=list[PermissionProfile],
    dependencies=(
        has_permission(Permissions.users_management_read),
        has_permission(Permissions.permissions_management_read),
    ),
)
def read_user_permissions(user_id: int, context: UserContext) -> list[Permission]:
    """Get all effective permissions for a specific user."""
    user = crud_users.get_if_exist(entity_id=user_id, context=context)
    return crud_users.get_permissions(user=user)


@users_router.get(
    "/{user_id}/roles",
    response_model=list[RoleProfile],
    dependencies=(
        has_permission(
            Permissions.users_management_read,
            Permissions.roles_management_read,
        ),
    ),
)
def read_user_roles(user_id: int, context: UserContext) -> list[Role]:
    """Get all roles assigned to a specific user."""
    user = crud_users.get_if_exist(entity_id=user_id, context=context)
    return crud_users.get_roles(user=user)


@users_router.put(
    "/{user_id}/password",
    response_model=UserProfile,
    dependencies=(has_permission(Permissions.password_management_update),),
)
def update_password(user_id: int, obj_in: UserPasswordChange, context: UserContext) -> User:
    """Update user's password (admin operation)."""
    return crud_users.change_password(user_id=user_id, obj_in=obj_in, context=context)


__all__ = ["users_router"]
