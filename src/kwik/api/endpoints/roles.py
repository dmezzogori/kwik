"""Role management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.crud import crud_permissions, crud_roles, crud_users
from kwik.dependencies import ListQuery, UserContext, has_permission
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
def read_roles(q: ListQuery, context: UserContext) -> Paginated[RoleProfile]:
    """Retrieve roles."""
    total, data = crud_roles.get_multi(context=context, **q)
    return {"total": total, "data": data}


@roles_router.post(
    "/",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_create),),
)
def create_role(role_in: RoleDefinition, context: UserContext) -> Role:
    """Create new role."""
    role = crud_roles.get_by_name(name=role_in.name, context=context)
    if role is not None:
        raise DuplicatedEntityError

    return crud_roles.create(obj_in=role_in, context=context)


@roles_router.get(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_read),),
)
def read_role_by_id(role_id: int, context: UserContext) -> Role:
    """Get a specific role by id."""
    return crud_roles.get_if_exist(entity_id=role_id, context=context)


@roles_router.put(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_update),),
)
def update_role(role_id: int, role_in: RoleUpdate, context: UserContext) -> Role:
    """Update a role."""
    return crud_roles.update(entity_id=role_id, obj_in=role_in, context=context)


@roles_router.delete(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_delete),),
)
def delete_role(role_id: int, context: UserContext) -> Role:
    """Delete a role."""
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    return crud_roles.delete(entity_id=role.id, context=context)


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
def read_permissions_by_role(role_id: int, context: UserContext) -> list[Permission]:
    """Get permissions associated to a role."""
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
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
def read_available_permissions_for_role(role_id: int, context: UserContext) -> list[Permission]:
    """Get all permissions available to assign to the given role."""
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    return crud_roles.get_permissions_assignable_to(role=role, context=context)


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
def users_with_role(role_id: int, context: UserContext) -> list[User]:
    """Get users associated to a role."""
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
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
def available_users_for_role(role_id: int, context: UserContext) -> list[User]:
    """Get users available to assign to a role."""
    return crud_roles.get_users_without(role_id=role_id, context=context)


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
def assign_permission_to_role(role_id: int, assignment: RolePermissionAssignment, context: UserContext) -> Role:
    """
    Assign a permission to a role.

    Raises:
        NotFound: If the provided role or permission does not exist

    Permissions required:
        * `roles_management_update`
        * `permissions_management_update`

    """
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    permission = crud_permissions.get_if_exist(entity_id=assignment.permission_id, context=context)
    return crud_roles.assign_permission(role=role, permission=permission, context=context)


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
def remove_permission_from_role(role_id: int, permission_id: int, context: UserContext) -> Role:
    """
    Remove a permission from a role.

    Raises:
        NotFound: If the provided role or permission does not exist

    Permissions required:
        * `roles_management_update`
        * `permissions_management_update`

    """
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    permission = crud_permissions.get_if_exist(entity_id=permission_id, context=context)
    return crud_roles.remove_permission(role=role, permission=permission, context=context)


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
def assign_user_to_role(role_id: int, assignment: RoleUserAssignment, context: UserContext) -> Role:
    """
    Assign a user to a role.

    Raises:
        NotFound: If the provided role or user does not exist

    Permissions required:
        * `roles_management_update`
        * `users_management_update`

    """
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    user = crud_users.get_if_exist(entity_id=assignment.user_id, context=context)
    return crud_roles.assign_user(role=role, user=user, context=context)


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
def remove_user_from_role(role_id: int, user_id: int, context: UserContext) -> Role:
    """
    Remove a user from a role.

    Raises:
        NotFound: If the provided role or user does not exist

    Permissions required:
        * `roles_management_update`
        * `users_management_update`

    """
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    user = crud_users.get_if_exist(entity_id=user_id, context=context)
    return crud_roles.remove_user(role=role, user=user, context=context)


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
def remove_all_permissions_from_role(role_id: int, context: UserContext) -> Role:
    """
    Remove all permission associations from a role.

    Does not delete the role itself.

    Raises:
        NotFound: If the provided role does not exist

    Permissions required:
        * `roles_management_delete`
        * `permissions_management_delete`

    """
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    return crud_roles.remove_all_permissions(role=role, context=context)


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
def remove_all_users_from_role(role_id: int, context: UserContext) -> Role:
    """
    Remove all user associations from a role.

    Does not delete the role itself.

    Raises:
        NotFound: If the provided role does not exist

    Permissions required:
        * `roles_management_delete`
        * `users_management_delete`

    """
    role = crud_roles.get_if_exist(entity_id=role_id, context=context)
    return crud_roles.remove_all_users(role=role, context=context)


__all__ = ["roles_router"]
