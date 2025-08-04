"""User management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kwik.typings
from kwik.api.deps import Pagination, current_user, has_permission
from kwik.core.enum import Permissions
from kwik.crud import roles, users
from kwik.exceptions import DuplicatedEntity, Forbidden
from kwik.routers import AuditorRouter
from kwik.schemas import (
    Paginated,
    PermissionProfile,
    RoleProfile,
    UserPasswordChange,
    UserProfile,
    UserProfileUpdate,
    UserRegistration,
    UserRoleAssignment,
)

if TYPE_CHECKING:
    from kwik.models import Permission, Role, User

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


@router.get("/me/roles", response_model=list[RoleProfile])
def read_roles_of_current_user(user: current_user) -> list[Role]:
    """Get roles of the current logged-in user."""
    return roles.get_multi_by_user_id(user_id=user.id)


@router.get(
    "/{user_id}/roles",
    response_model=list[RoleProfile],
    dependencies=(has_permission(Permissions.roles_management_read),),
)
def read_user_roles(user_id: int) -> list[Role]:
    """Get all roles assigned to a specific user."""
    users.get_if_exist(id=user_id)  # Ensure user exists
    return roles.get_multi_by_user_id(user_id=user_id)


@router.post(
    "/{user_id}/roles",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_update),),
)
def assign_role_to_user(user_id: int, role_assignment: UserRoleAssignment) -> Role:
    """Assign a role to a user."""
    user_db = users.get_if_exist(id=user_id)
    role_db = roles.get_if_exist(id=role_assignment.role_id)
    return roles.associate_user(user_db=user_db, role_db=role_db)


@router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_update),),
)
def remove_role_from_user(user_id: int, role_id: int) -> Role:
    """Remove a role from a user."""
    user_db = users.get_if_exist(id=user_id)
    role_db = roles.get_if_exist(id=role_id)
    return roles.purge_user(user_db=user_db, role_db=role_db)


@router.get("/me/permissions", response_model=list[PermissionProfile])
def read_permissions_of_current_user(user: current_user) -> list[Permission]:
    """Get all effective permissions of the current logged-in user."""
    return users.get_permissions(user_id=user.id)


@router.get(
    "/{user_id}/permissions",
    response_model=list[PermissionProfile],
    dependencies=(has_permission(Permissions.permissions_management_read),),
)
def read_user_permissions(user_id: int) -> list[Permission]:
    """Get all effective permissions for a specific user."""
    users.get_if_exist(id=user_id)  # Ensure user exists
    return users.get_permissions(user_id=user_id)
