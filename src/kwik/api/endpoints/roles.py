"""Role management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kwik.typings
from kwik.api.deps import Pagination, has_permission
from kwik.core.enum import Permissions
from kwik.crud import crud_permissions, crud_roles, crud_users
from kwik.exceptions import DuplicatedEntityError
from kwik.routers import AuthenticatedRouter
from kwik.schemas import (
    Paginated,
    PermissionProfile,
    RoleDefinition,
    RolePermissionAssignment,
    RoleProfile,
    RoleUpdate,
    RoleUserAssignment,
    UserProfile,
)

if TYPE_CHECKING:
    from kwik.models import Permission, Role, User

roles_router = AuthenticatedRouter(prefix="/roles")


@roles_router.get(
    "/",
    response_model=Paginated[RoleProfile],
    dependencies=(has_permission(Permissions.roles_management_read),),
)
def read_roles(paginated: Pagination) -> kwik.typings.PaginatedResponse[Role]:
    """Retrieve roles."""
    total, data = crud_roles.get_multi(**paginated)
    return kwik.typings.PaginatedResponse(data=data, total=total)


@roles_router.post(
    "/",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_create),),
)
def create_role(role_in: RoleDefinition) -> Role:
    """Create new role."""
    role = crud_roles.get_by_name(name=role_in.name)
    if role is not None:
        raise DuplicatedEntityError

    return crud_roles.create(obj_in=role_in)


@roles_router.get(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_read),),
)
def read_role_by_id(role_id: int) -> Role:
    """Get a specific role by id."""
    return crud_roles.get_if_exist(id=role_id)


@roles_router.put(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_update),),
)
def update_role(role_id: int, role_in: RoleUpdate) -> Role:
    """Update a role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.update(db_obj=role, obj_in=role_in)


@roles_router.delete(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_delete),),
)
def delete_role(role_id: int) -> Role:
    """Delete a role."""
    crud_roles.get_if_exist(id=role_id)
    return crud_roles.delete(id=role_id)


@roles_router.get(
    "/{role_id}/permissions",
    response_model=list[PermissionProfile],
    dependencies=(
        has_permission(
            Permissions.roles_management_read,
            Permissions.permissions_management_read,
        ),
    ),
)
def read_permissions_by_role(role_id: int) -> list[Permission]:
    """Get permissions associated to a role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.get_permissions_assigned_to(role=role)


@roles_router.get(
    "/{role_id}/available-permissions",
    response_model=list[PermissionProfile],
    dependencies=(
        has_permission(
            Permissions.roles_management_read,
            Permissions.permissions_management_read,
        ),
    ),
)
def read_available_permissions_for_role(role_id: int) -> list[Permission]:
    """Get all permissions available to assign to the given role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.get_permissions_assignable_to(role=role)


@roles_router.get(
    "/{role_id}/users",
    response_model=list[UserProfile],
    dependencies=(
        has_permission(
            Permissions.users_management_read,
            Permissions.roles_management_read,
        ),
    ),
)
def users_with_role(role_id: int) -> list[User]:
    """Get users associated to a role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.get_users_with(role=role)


@roles_router.get(
    "/{role_id}/available-users",
    response_model=list[UserProfile],
    dependencies=(
        has_permission(
            Permissions.users_management_read,
            Permissions.roles_management_read,
        ),
    ),
)
def available_users_for_role(role_id: int) -> list[User]:
    """Get users available to assign to a role."""
    return crud_roles.get_users_without(role_id=role_id)


@roles_router.post(
    "/{role_id}/permissions",
    response_model=RoleProfile,
    dependencies=(
        has_permission(
            Permissions.roles_management_update,
            Permissions.permissions_management_update,
        ),
    ),
)
def assign_permission_to_role(role_id: int, assignment: RolePermissionAssignment) -> Role:
    """
    Assign a permission to a role.

    Raises:
        NotFound: If the provided role or permission does not exist

    Permissions required:
        * `roles_management_update`
        * `permissions_management_update`

    """
    role = crud_roles.get_if_exist(id=role_id)
    permission = crud_permissions.get_if_exist(id=assignment.permission_id)
    return crud_roles.assign_permission(role=role, permission=permission)


@roles_router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleProfile,
    dependencies=(
        has_permission(
            Permissions.roles_management_update,
            Permissions.permissions_management_update,
        ),
    ),
)
def remove_permission_from_role(role_id: int, permission_id: int) -> Role:
    """
    Remove a permission from a role.

    Raises:
        NotFound: If the provided role or permission does not exist

    Permissions required:
        * `roles_management_update`
        * `permissions_management_update`

    """
    role = crud_roles.get_if_exist(id=role_id)
    permission = crud_permissions.get_if_exist(id=permission_id)
    return crud_roles.remove_permission(role=role, permission=permission)


@roles_router.post(
    "/{role_id}/users",
    response_model=RoleProfile,
    dependencies=(
        has_permission(
            Permissions.roles_management_update,
            Permissions.users_management_update,
        ),
    ),
)
def assign_user_to_role(role_id: int, assignment: RoleUserAssignment) -> Role:
    """
    Assign a user to a role.

    Raises:
        NotFound: If the provided role or user does not exist

    Permissions required:
        * `roles_management_update`
        * `users_management_update`

    """
    role = crud_roles.get_if_exist(id=role_id)
    user = crud_users.get_if_exist(id=assignment.user_id)
    return crud_roles.assign_user(role=role, user=user)


@roles_router.delete(
    "/{role_id}/users/{user_id}",
    response_model=RoleProfile,
    dependencies=(
        has_permission(
            Permissions.roles_management_update,
            Permissions.users_management_update,
        ),
    ),
)
def remove_user_from_role(role_id: int, user_id: int) -> Role:
    """
    Remove a user from a role.

    Raises:
        NotFound: If the provided role or user does not exist

    Permissions required:
        * `roles_management_update`
        * `users_management_update`

    """
    role = crud_roles.get_if_exist(id=role_id)
    user = crud_users.get_if_exist(id=user_id)
    return crud_roles.remove_user(role=role, user=user)


@roles_router.delete(
    "/{role_id}/permissions",
    response_model=RoleProfile,
    dependencies=(
        has_permission(
            Permissions.roles_management_delete,
            Permissions.permissions_management_delete,
        ),
    ),
)
def remove_all_permissions_from_role(role_id: int) -> Role:
    """
    Remove all permission associations from a role.

    Does not delete the role itself.

    Raises:
        NotFound: If the provided role does not exist

    Permissions required:
        * `roles_management_delete`
        * `permissions_management_delete`

    """
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.remove_all_permissions(role=role)


@roles_router.delete(
    "/{role_id}/users",
    response_model=RoleProfile,
    dependencies=(
        has_permission(
            Permissions.roles_management_delete,
            Permissions.users_management_delete,
        ),
    ),
)
def remove_all_users_from_role(role_id: int) -> Role:
    """
    Remove all user associations from a role.

    Does not delete the role itself.

    Raises:
        NotFound: If the provided role does not exist

    Permissions required:
        * `roles_management_delete`
        * `users_management_delete`

    """
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.deprecate(role=role)


__all__ = ["roles_router"]
